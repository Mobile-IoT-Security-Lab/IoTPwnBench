#!/usr/bin/env python3
"""Run the builds planned by scripts/build-all.sh on several workers at once.

Every worker has its own BitBake build directory (a Docker volume named
yocto-build-w<N>), so builds do not block each other, while all workers share
the download and sstate cache in the yocto-cache volume.

  scripts/build-farm.py -j 4 [build-all.sh options]

Options other than -j and --log-dir go to build-all.sh, so the plan is the same,
for example "-j 4 --fixed -m qemuarm64 -s 'cwe120-*'". Builds that already have
an exported rootfs are skipped. Results are written to <log-dir>/results.json.
"""
import argparse
import json
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
LINE = re.compile(r"^YOCTO_MACHINE=(\S+) FIRMWARE=(\S+) (.*) docker compose run --rm(.*) yocto$")


def plan(options):
    result = subprocess.run(["sh", str(ROOT / "scripts/build-all.sh"), "--dry-run"] + options,
                            cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(result.stderr)
    items = []
    for line in result.stdout.splitlines():
        match = LINE.match(line)
        if not match:
            sys.exit(f"unexpected plan line: {line}")
        machine, firmware, env, extra = match.groups()
        items.append((machine, firmware, env, extra.split()))
    return items


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-j", "--jobs", type=int, default=4)
    parser.add_argument("--log-dir", type=Path, default=ROOT / "build-logs")
    args, options = parser.parse_known_args()
    args.log_dir.mkdir(parents=True, exist_ok=True)
    work = queue.Queue()
    skipped = 0
    for machine, firmware, env, extra in plan(options):
        rootfs = ROOT / f"deploy-images/{firmware}/{machine}/iotbench-{firmware}-{machine}.rootfs.ext4.zst"
        if rootfs.exists():
            skipped += 1
            continue
        work.put((machine, firmware, env, extra))
    total = work.qsize()
    print(f"{total} builds on {args.jobs} workers, {skipped} already exported", flush=True)
    results, lock, started = {}, threading.Lock(), time.time()

    def worker(number):
        while True:
            try:
                machine, firmware, env, extra = work.get_nowait()
            except queue.Empty:
                return
            environment = dict(item.split("=", 1) for item in env.split())
            command = ["docker", "compose", "run", "--rm", "-v", f"yocto-build-w{number}:/workdir"] + extra + ["yocto"]
            log = args.log_dir / f"{firmware}.{machine}.log"
            begin = time.time()
            with log.open("w") as handle:
                code = subprocess.run(command, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT,
                                      env={**__import__("os").environ, "YOCTO_MACHINE": machine,
                                           "FIRMWARE": firmware, **environment}).returncode
            with lock:
                results[f"{firmware}/{machine}"] = {"ok": code == 0, "seconds": round(time.time() - begin), "log": str(log)}
                done = len(results)
                failed = sum(1 for r in results.values() if not r["ok"])
                print(f"[{done}/{total}] {'ok' if code == 0 else 'FAILED'} {firmware} ({machine}) "
                      f"{round(time.time() - begin)}s, {failed} failed, {round((time.time() - started) / 60)} min",
                      flush=True)
                (args.log_dir / "results.json").write_text(json.dumps(results, indent=1))

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(args.jobs)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return 1 if any(not r["ok"] for r in results.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
