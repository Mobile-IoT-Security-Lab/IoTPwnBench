#!/usr/bin/env python3
"""Boot exported sudo traversal fixtures and test real sudo on the guest console.

Requires QEMU, zstd and Python 3 on a POSIX host. Uses the repository's existing
run-qemu.sh and environment selectors; creates only disposable QEMU snapshots.
"""

import argparse
import os
from pathlib import Path
import pty
import select
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
WARNING = (
    "INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — "
    "LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT"
)


def verify(device, timeout):
    firmware = f"{device}-cwe022-bad-sudo-rights"
    environment = dict(os.environ, FIRMWARE=firmware, QEMU_PERSIST="0")
    master, slave = pty.openpty()
    transcript = bytearray()
    process = None
    log_path = Path(tempfile.gettempdir()) / f"iotbench-sudo-{device}-qemu.log"
    try:
        process = subprocess.Popen(
            [str(ROOT / "scripts/run-qemu.sh")], cwd=ROOT, env=environment,
            stdin=slave, stdout=slave, stderr=slave,
        )
        os.close(slave)
        slave = None
        position = 0

        def wait_for(token):
            nonlocal position
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                index = transcript.find(token, position)
                if index >= 0:
                    position = index + len(token)
                    return
                if process.poll() is not None:
                    raise RuntimeError(f"QEMU exited with status {process.returncode}")
                ready, _, _ = select.select([master], [], [], 1)
                if ready:
                    transcript.extend(os.read(master, 65536))
            raise TimeoutError(f"Timed out waiting for {token!r}")

        wait_for(b"login:")
        os.write(master, b"root\n")
        wait_for(b"Password:")
        os.write(master, b"routeradmin\n")
        wait_for(b"root@")
        if WARNING.encode() not in transcript:
            raise AssertionError("Fixture warning missing from guest login banner")
        # Device comes only from discovered recipe names, validated by main().
        command = (
            f"sh /usr/share/iotbench/bad-sudo-rights/test-guest.sh {device}; "
            "printf '\\nIOTBENCH_TEST_EXIT=%s\\n' \"$?\"\n"
        )
        os.write(master, command.encode())
        wait_for(b"IOTBENCH_TEST_EXIT=0")
        # Check the actual test output, not just the exit marker.
        if transcript.count(b"PASS ") != 5:
            raise AssertionError(f"Expected five guest PASS lines; got {transcript.count(b'PASS ')}")
        print(f"PASS {firmware}: real sudo traversal and containment; log {log_path}", flush=True)
    except Exception as error:
        raise RuntimeError(f"{firmware}: {error}; console log {log_path}") from error
    finally:
        if slave is not None:
            os.close(slave)
        if process is not None and process.poll() is None:
            os.write(master, b"\x01x")
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=10)
        os.close(master)
        log_path.write_bytes(transcript)


def main():
    devices = sorted(
        recipe.name.removeprefix("iotbench-").removesuffix("-cwe022-bad-sudo-rights.bb")
        for recipe in (ROOT / "meta-iotbench/recipes-images").glob("iotbench-*-cwe022-bad-sudo-rights.bb")
    )
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--device", choices=devices)
    selection.add_argument("--all", action="store_true", help="test every supported device sequentially")
    parser.add_argument("--timeout", type=int, default=150, help="maximum seconds per console step")
    arguments = parser.parse_args()
    for device in devices if arguments.all else [arguments.device]:
        verify(device, arguments.timeout)


if __name__ == "__main__":
    main()
