#!/usr/bin/env python3
"""Boot exported FTP write-rights fixtures and test real FTP on the guest console.

Requires Python 3 and either native QEMU/zstd or the built Docker/Yocto runtime.
Selects the available repository launcher; creates only disposable QEMU snapshots.
"""

import argparse
import os
from pathlib import Path
import pty
import select
import shutil
import errno
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]



def verify(device, timeout, backend='auto'):
    firmware = f"{device}-cwe276-bad-write-rights"
    environment = dict(os.environ, FIRMWARE=firmware, QEMU_PERSIST="0")
    machine = environment.get("YOCTO_MACHINE", "qemuarm64")
    binaries = {"qemuarm64": "qemu-system-aarch64", "qemuarm": "qemu-system-arm",
                "qemux86-64": "qemu-system-x86_64", "qemux86": "qemu-system-i386",
                "qemumips": "qemu-system-mips"}
    if machine not in binaries:
        raise ValueError("Unsupported machine: " + machine)
    if backend == "auto":
        backend = "native" if shutil.which(binaries[machine]) and shutil.which("zstd") else "docker"
    launcher = ROOT / ("scripts/run-qemu-docker.sh" if backend == "docker" else "scripts/run-qemu.sh")
    container = f"iotbench-qemu-{firmware}-{machine}"
    if backend == "docker":
        if not shutil.which("docker"):
            raise RuntimeError("Install native QEMU/zstd or use the built Docker/Yocto runtime")
        if subprocess.check_output(["docker", "ps", "-aq", "--filter", f"name=^/{container}$"]).strip():
            raise RuntimeError("QEMU container is already in use: " + container)
    master, slave = pty.openpty()
    transcript = bytearray()
    process = None
    log_path = Path(tempfile.gettempdir()) / f"iotbench-ftp-{device}-qemu.log"
    try:
        process = subprocess.Popen(
            [str(launcher)], cwd=ROOT, env=environment,
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
                    try:
                        data = os.read(master, 65536)
                    except OSError as error:
                        if error.errno == errno.EIO:
                            raise RuntimeError(transcript.decode(errors="replace").strip()) from error
                        raise
                    if not data:
                        raise RuntimeError("QEMU console closed")
                    transcript.extend(data.replace(b"\r", b""))
            raise TimeoutError(f"Timed out waiting for {token!r}")

        wait_for(b"login:")
        os.write(master, b"root\n")
        wait_for(b"Password:")
        os.write(master, b"routeradmin\n")
        wait_for(b"root@")
        # Device comes only from discovered recipe names, validated by main().
        command = (
            f"python3 /usr/share/iotbench/bad-write-rights/test-guest.py --isolated-fixture; "
            "printf '\\nIOTBENCH_TEST_EXIT=%s\\n' \"$?\"\n"
        )
        os.write(master, command.encode())
        wait_for(b"\nIOTBENCH_TEST_EXIT=")
        result_start = position
        wait_for(b"\n")
        result = transcript[result_start:position].strip()
        if result != b"0":
            raise RuntimeError("Guest FTP test failed with exit " + result.decode(errors="replace"))
        # Check the actual test output, not just the exit marker.
        if transcript.count(b"PASS ") != 5:
            raise AssertionError(f"Expected five guest PASS lines; got {transcript.count(b'PASS ')}")
        print(f"PASS {firmware}: real FTP write-rights and containment; log {log_path}", flush=True)
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
                if backend == "docker":
                    subprocess.run(["docker", "stop", "--time", "5", container], check=False,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    process.terminate()
                process.wait(timeout=15)
        os.close(master)
        log_path.write_bytes(transcript)


def main():
    devices = sorted(
        recipe.name[len("iotbench-"):-len("-cwe276-bad-write-rights.bb")]
        for recipe in (ROOT / "meta-iotbench/recipes-images").glob("iotbench-*-cwe276-bad-write-rights.bb")
    )
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--device", choices=devices)
    selection.add_argument("--all", action="store_true", help="test every supported device sequentially")
    parser.add_argument("--timeout", type=int, default=150, help="maximum seconds per console step")
    parser.add_argument("--build", action="store_true", help="build and export each opted-in synthetic fixture before testing")
    parser.add_argument("--qemu-backend", choices=("auto", "native", "docker"), default="auto")
    arguments = parser.parse_args()
    for device in devices if arguments.all else [arguments.device]:
        if arguments.build:
            subprocess.run(
                ["docker", "compose", "run", "--rm", "-e",
                 "IOTBENCH_ENABLE_FTP_WRITE_FIXTURE=1", "yocto"],
                cwd=ROOT, env=dict(os.environ, FIRMWARE=f"{device}-cwe276-bad-write-rights"),
                check=True,
            )
        verify(device, arguments.timeout, arguments.qemu_backend)


if __name__ == "__main__":
    main()
