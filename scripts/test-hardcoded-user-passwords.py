#!/usr/bin/env python3
"""Inspect a CWE-798 ext4 fixture offline or run local authentication in QEMU.

Offline inspection never mounts or executes firmware. Runtime verification uses
the existing serial-console harness and disposable snapshots, without a remote
authentication service. Python 3 standard library only.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import pty
import re
import select
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / "meta-iotbench"
if not LAYER.is_dir():
    LAYER = Path("/opt/yocto/layers/meta-iotbench")
DEVICES = sorted(p.parent.name for p in (LAYER / "recipes-devices").glob("*/device-*.inc"))
SLUG = "cwe798-hardcoded-user-passwords"
ACCOUNTS = "/etc/iotbench/hardcoded-user-passwords/accounts.conf"
HELPER = "/usr/bin/iotbench-fixture-auth"
DATA = "/usr/share/iotbench/hardcoded-user-passwords"
WARNING = ("INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — "
           "LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def verify_image(path, debugfs):
    require(path.is_file(), f"Image not found: {path}")
    require(shutil.which(debugfs), f"debugfs not found: {debugfs}")
    with tempfile.TemporaryDirectory(prefix="iotbench-user-passwords-") as temporary:
        image = path.resolve()
        if path.suffix == ".zst":
            image = Path(temporary) / "rootfs.ext4"
            subprocess.run(["zstd", "-q", "-d", str(path), "-o", str(image)], check=True)

        def inspect(operation, name):
            result = subprocess.run([debugfs, "-R", f"{operation} {name}", str(image)],
                                    capture_output=True, check=True)
            require(b"File not found" not in result.stderr, f"Missing image path: {name}")
            return result.stdout.decode()

        def metadata(name):
            info = inspect("stat", name)
            mode = re.search(r"Mode:\s+([0-7]+)\b", info)
            owner = re.search(r"User:\s+(\d+)\s+Group:\s+(\d+)\b", info)
            require(mode and owner, f"Cannot parse inode: {name}")
            return int(mode[1], 8), int(owner[1]), int(owner[2])

        require(metadata(ACCOUNTS) == (0o600, 0, 0), "Account database must be root:root 0600")
        require(metadata(HELPER) == (0o755, 0, 0), "Helper must be ordinary root:root 0755")
        for parent in ("/", "/etc", "/etc/iotbench", str(Path(ACCOUNTS).parent), "/usr", "/usr/bin"):
            mode, uid, gid = metadata(parent)
            require(uid == gid == 0 and not mode & 0o022, f"Unsafe fixture ancestor: {parent}")
        require(inspect("cat", ACCOUNTS) == "fixtureuser:fixture-password-123\n",
                "Wrong embedded synthetic account/password")
        source = LAYER / "recipes-vulns" / SLUG / "files"
        helper = inspect("cat", HELPER)
        require(helper == (source / "iotbench-fixture-auth").read_text().replace("@SYSCONFDIR@", "/etc"),
                "Installed authentication consumer differs from the fixture source")
        test = inspect("cat", DATA + "/test-guest.sh")
        require(test == (source / "test-guest.sh").read_text().replace("@SYSCONFDIR@", "/etc")
                .replace("@BINDIR@", "/usr/bin"), "Installed guest verifier differs from source")
        truth = json.loads(inspect("cat", DATA + "/ground-truth.json"))
        expected = json.loads((source / "ground-truth.json").read_text()
                              .replace("@SYSCONFDIR@", "/etc").replace("@BINDIR@", "/usr/bin"))
        require(truth == expected, "Ground-truth metadata differs from the actual fixture")
        require(inspect("cat", DATA + "/NOTICE").splitlines()[0] == WARNING
                and WARNING in inspect("cat", "/etc/motd"), "Required warning missing")
        identity = inspect("cat", "/etc/iotbench/device.conf")
        device = re.search(r'^DEVICE_CLASS="([a-z]+)"$', identity, re.MULTILINE)
        require(device and device[1] in DEVICES, "Unsupported device identity")
        print(f"PASS {device[1]}: embedded fixtureuser password, matching authentication consumer, "
              "normal permissions, warning and CWE-798 ground truth", flush=True)
        print(f"PASS helper SHA-256 {hashlib.sha256(helper.encode()).hexdigest()}", flush=True)


def verify_guest(device, timeout):
    firmware = f"{device}-{SLUG}"
    environment = dict(os.environ, FIRMWARE=firmware, QEMU_PERSIST="0")
    master, slave = pty.openpty()
    transcript = bytearray()
    process = None
    log_path = ROOT / "deploy-images" / firmware / environment.get("YOCTO_MACHINE", "qemuarm64") / "validation-console.log"
    try:
        process = subprocess.Popen([str(ROOT / "scripts/run-qemu.sh")], cwd=ROOT,
                                   env=environment, stdin=slave, stdout=slave, stderr=slave)
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
        require(WARNING.encode() in transcript, "Required login warning missing")
        # Only a fixed synthetic test is run; device names come from profiles.
        command = (f"sh {DATA}/test-guest.sh {device}; "
                   "printf '\\nUSER_PASSWORD_CHECK_EXIT=%s\\n' \"$?\"\n")
        os.write(master, command.encode())
        wait_for(b"\r\nUSER_PASSWORD_CHECK_EXIT=")
        wait_for(b"\r\n")
        output = transcript.replace(b"\r", b"")
        require(re.search(rb"(?m)^USER_PASSWORD_CHECK_EXIT=0$", output), "Guest regression failed")
        require(len(re.findall(rb"(?m)^PASS ", output)) == 4, "Missing guest checks")
        print(f"PASS {firmware}: deterministic authentication, rejection checks, "
              f"credential consumption and fail-closed behavior; log {log_path}", flush=True)
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
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_bytes(transcript)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--image", type=Path, help="offline ext4 or ext4.zst inspection")
    selection.add_argument("--device", choices=DEVICES, help="boot and verify one device")
    selection.add_argument("--all", action="store_true", help="boot all device fixtures sequentially")
    parser.add_argument("--debugfs", default="debugfs", help="debugfs path for --image")
    parser.add_argument("--timeout", type=int, default=150, help="seconds per console step")
    arguments = parser.parse_args()
    if arguments.image:
        verify_image(arguments.image, arguments.debugfs)
    else:
        for device in DEVICES if arguments.all else [arguments.device]:
            verify_guest(device, arguments.timeout)


if __name__ == "__main__":
    main()
