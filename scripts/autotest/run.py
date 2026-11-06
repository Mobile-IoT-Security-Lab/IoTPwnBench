#!/usr/bin/env python3
"""Boot firmware images and check that each documented payload triggers its signal.

  scripts/autotest/run.py [--jobs N] [--machine M] firmware-id ...

A vulnerable image passes when its signal appears. A corrected twin (id ending in
-fixed) passes when the signal does not appear and the normal request still works.
Results go to build-logs/autotest.json.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guest import Guest, ROOT          # noqa: E402
from scenarios import SCENARIOS        # noqa: E402
from shared import SHARED              # noqa: E402


def run_payload(guest, payload):
    if isinstance(payload, tuple) and payload and payload[0] == "vi_sudo":
        if not getattr(guest, "logged_in", False):
            guest.login()
            guest.logged_in = True
        # The sudo password lecture (shown once per session) contains several bare
        # colons, so a loose "assword|~|:" match fires on the lecture text itself
        # before the real "Password:" prompt and the password is never sent; the
        # next thing typed (the id probe below) is then fed to sudo as a wrong
        # password, which it rejects with "Sorry, try again.". Wait for the
        # anchored "assword:" prompt instead, send the password exactly once, and
        # branch on whether sudo grants the command (vi's "~" empty-buffer screen)
        # or denies it ("Sorry, ... not allowed ...", expected on the fixed twin,
        # whose sudoers rule authorizes a different command).
        _, setup_command, start_command, password, shell_pattern = payload
        guest.send(setup_command + "\n")
        out = [guest.expect(shell_pattern, 30)]
        guest.send(start_command + "\n")
        out.append(guest.expect(r"assword:", 30))
        guest.send(password + "\n")
        out.append(guest.expect(r"~|not allowed", 30))
        if "not allowed" in guest.log[-1]:
            out.append(guest.expect(shell_pattern, 30))
            return "\n".join(out)
        guest.send(":!id\r")
        out.append(guest.expect(r"uid=0\(root\)|\(END\)|:", 30))
        guest.send("\r:q!\r")
        out.append(guest.expect(shell_pattern, 30))
        return "\n".join(out)
    if isinstance(payload, tuple) and payload and payload[0] == "interactive":
        if not getattr(guest, "logged_in", False):
            guest.login()
            guest.logged_in = True
        return guest.interactive(payload[1], 30)
    if isinstance(payload, tuple) and payload and payload[0] == "guest":
        if not getattr(guest, "logged_in", False):
            guest.login()
            guest.logged_in = True
        outputs = []
        for command in payload[1]:
            outputs.append(guest.run(command, payload[3] if len(payload) > 3 else 280)[0])
        if payload[2]:
            time.sleep(payload[2])
        return "\n".join(outputs)
    return guest.host(payload)


def check_embedded_auth(firmware, machine, variant, twin=False):
    """Root is locked on this family by design; inspect the exported rootfs offline."""
    begin = time.time()
    archive = ROOT / f"deploy-images/{firmware}/{machine}/iotbench-{firmware}-{machine}.rootfs.ext4.zst"
    if not archive.is_file():
        return {"status": "error", "error": "rootfs not exported", "seconds": 0}
    try:
        with tempfile.TemporaryDirectory(prefix="iotbench-inspect-") as temporary:
            tmp = Path(temporary)
            image = tmp / "image.ext4"
            rootfs = tmp / "rootfs"
            rootfs.mkdir()
            with open(image, "wb") as handle:
                subprocess.run(["zstd", "-dc", str(archive)], stdout=handle, check=True, timeout=120)
            subprocess.run(["debugfs", "-R", f"rdump / {rootfs}", str(image)],
                           capture_output=True, text=True, timeout=120)
            result = subprocess.run(
                ["python3", str(ROOT / ("scripts/test-embedded-auth-twin.py" if twin
                                       else "scripts/test-embedded-auth-fixture.py")),
                 "--isolated-fixture", "--rootfs", str(rootfs), "--variant", variant],
                capture_output=True, text=True, timeout=120)
            out = (result.stdout + result.stderr)[-2000:]
            return {"status": "pass" if result.returncode == 0 else "fail", "output": out,
                   "seconds": round(time.time() - begin)}
    except Exception as error:  # noqa: BLE001
        return {"status": "error", "error": str(error)[-2000:], "seconds": round(time.time() - begin)}


def check(firmware, machine):
    twin = firmware.endswith("-fixed")
    base = firmware.removesuffix("-fixed")
    device, _, slug = base.partition("-")
    if slug.startswith("cwe798-embedded-auth-"):
        return check_embedded_auth(firmware, machine, slug[len("cwe798-embedded-auth-"):], twin)
    spec = SCENARIOS.get(base) or (SHARED[slug](device) if slug in SHARED else None)
    if spec is None:
        return {"status": "no-spec"}
    kind, payload, signal, normal, normal_signal = spec
    guest = Guest(firmware, machine)
    begin = time.time()
    try:
        guest.expect(r"login: ", 900)
        guest.buffer = "login: " + guest.buffer
        # Give the services time to start after the login prompt.
        time.sleep(25)
        out = run_payload(guest, payload)
        hit = re.search(signal, out, re.S) is not None
        result = {"signal": hit, "output": out[-2000:]}
        if normal:
            out2 = run_payload(guest, normal)
            result["normal"] = re.search(normal_signal, out2, re.S) is not None
        if kind == "selftest":
            result["status"] = "no-test" if "SELFTEST_NONE" in out else ("pass" if hit else "fail")
        else:
            result["status"] = ("pass" if not hit and result.get("normal", True) else "fail") if twin else ("pass" if hit else "fail")
        result["seconds"] = round(time.time() - begin)
        return result
    except Exception as error:  # noqa: BLE001
        return {"status": "error", "error": str(error)[-2000:], "seconds": round(time.time() - begin)}
    finally:
        guest.stop()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("firmware", nargs="*")
    parser.add_argument("--watch", action="store_true",
                        help="keep testing every exported image that has a spec until the build farm has finished")
    parser.add_argument("--machine", default="qemuarm64")
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    out = ROOT / "build-logs/autotest.json"
    results = json.loads(out.read_text()) if out.exists() else {}

    def pending():
        found = []
        for rootfs in sorted((ROOT / "deploy-images").glob(f"*/{args.machine}/*.rootfs.ext4.zst")):
            firmware = rootfs.parent.parent.name
            key = f"{firmware}/{args.machine}"
            base = firmware.removesuffix("-fixed")
            slug = base.partition("-")[2]
            # The embedded-auth family has no guest spec, check() inspects its rootfs offline.
            known = base in SCENARIOS or slug in SHARED or slug.startswith("cwe798-embedded-auth-")
            if known and (key not in results or results[key]["status"] in ("error", "no-spec")):
                found.append(firmware)
        return found

    def farm_running():
        return subprocess.run(["pgrep", "-f", "build-farm.py"], capture_output=True).returncode == 0

    while True:
        batch = args.firmware if args.firmware and not args.watch else pending()
        if batch:
            with ThreadPoolExecutor(args.jobs) as pool:
                for firmware, result in zip(batch, pool.map(lambda f: check(f, args.machine), batch)):
                    results[f"{firmware}/{args.machine}"] = result
                    print(f"{result['status']:8} {firmware} {result.get('output', result.get('error', ''))[:100]!r}", flush=True)
                    out.write_text(json.dumps(results, indent=1))
        if not args.watch:
            return
        if not batch and not farm_running():
            print("watch finished: the farm is idle and every exported image with a spec was tested", flush=True)
            return
        if not batch:
            time.sleep(120)


if __name__ == "__main__":
    main()
