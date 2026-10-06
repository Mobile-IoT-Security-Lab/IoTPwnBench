#!/usr/bin/env python3
"""Verify synthetic SUID metadata offline, or benign identity reporting in QEMU.

--image reads an ext4 or ext4.zst image with debugfs, without mounting it or
executing its contents. --device/--all boot disposable QEMU snapshots using
the existing run-qemu.sh and normal environment selectors.
"""

import argparse
import json
import os
from pathlib import Path
import pty
import re
import select
import shutil
import stat
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
SLUG = "cwe250-dangerous-suid-rights"
HELPER = "/usr/bin/iotbench-suid-fixture"
DATA = "/usr/share/iotbench/dangerous-suid-rights"
WARNING = (
    "INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — "
    "LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT"
)
LAYER = ROOT / "meta-iotbench"
if not LAYER.is_dir():
    # Compose mounts /scripts separately from the existing Yocto layer.
    LAYER = Path("/opt/yocto/layers/meta-iotbench")
DEVICES = sorted(profile.parent.name for profile in
                 (LAYER / "recipes-devices").glob("*/device-*.inc"))


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def verify_image(path, debugfs):
    require(path.is_file(), f"Image not found: {path}")
    require(shutil.which(debugfs), f"debugfs not found: {debugfs}")
    with tempfile.TemporaryDirectory(prefix="iotbench-suid-inspect-") as temporary:
        image = path.resolve()
        if path.suffix == ".zst":
            image = Path(temporary) / "rootfs.ext4"
            subprocess.run(["zstd", "-q", "-d", str(path), "-o", str(image)], check=True)

        def inspect(operation, name):
            result = subprocess.run([debugfs, "-R", f"{operation} {name}", str(image)],
                                    capture_output=True, check=True)
            require(b"File not found" not in result.stderr, f"Missing image path: {name}")
            return result.stdout.decode()

        def permissions(name):
            details = inspect("stat", name)
            mode = re.search(r"Mode:\s+([0-7]+)\b", details)
            owner = re.search(r"User:\s+(\d+)\s+Group:\s+(\d+)\b", details)
            require(mode and owner, f"Cannot parse inode metadata: {details}")
            return int(mode[1], 8), int(owner[1]), int(owner[2])

        require(permissions(HELPER) == (0o4755, 0, 0),
                "Synthetic helper must be root:root 4755 (-rwsr-xr-x)")
        for parent in ("/", "/usr", "/usr/bin", "/usr/share", "/usr/share/iotbench", DATA):
            mode, uid, gid = permissions(parent)
            require(uid == gid == 0 and mode & stat.S_IXOTH and not mode & 0o022,
                    f"Fixture ancestor must be root-owned, traversable and not publicly writable: {parent}")
        require(permissions("/usr/bin/setpriv.util-linux") == (0o755, 0, 0),
                "Verification utility must remain ordinary non-SUID root:root 0755")
        print("PASS root ownership, executable mode 4755, SUID bit and accessible ancestors", flush=True)

        users = [line.split(":") for line in inspect("cat", "/etc/passwd").splitlines()
                 if line.startswith("suidfixture:")]
        require(len(users) == 1 and users[0][2:4] == ["993", "993"]
                and users[0][-1] == "/bin/false", "Wrong unprivileged fixture account")
        passwords = [line.split(":")[1] for line in inspect("cat", "/etc/shadow").splitlines()
                     if line.startswith("suidfixture:")]
        require(passwords == ["!"], "Fixture account must have a locked password")
        for group in inspect("cat", "/etc/group").splitlines():
            fields = group.split(":")
            require("suidfixture" not in fields[3].split(",") or fields[2] == "993",
                    "Unexpected supplementary group grants for fixture user")
        truth = json.loads(inspect("cat", DATA + "/ground-truth.json"))
        expected = {
            "warning": WARNING, "cwe": "CWE-250", "executable": HELPER,
            "ground_truth_label": "Privilege escalation risk caused by dangerous SUID rights",
            "owner_uid": 0, "group_gid": 0, "mode_octal": "4755", "suid": True,
            "unprivileged_uid": 993, "exploitation_chain": False,
        }
        require(all(truth.get(key) == value for key, value in expected.items()),
                "Ground-truth metadata does not match the fixture")
        require(inspect("cat", DATA + "/NOTICE").splitlines()[0] == WARNING
                and WARNING in inspect("cat", "/etc/motd"), "Required warning missing")
        identity = inspect("cat", "/etc/iotbench/device.conf")
        device = re.search(r'^DEVICE_CLASS="([a-z]+)"$', identity, re.MULTILINE)
        require(device and device[1] in DEVICES, "Unsupported device identity")
        helper = Path(temporary) / "helper.elf"
        inspect("dump", f"{HELPER} {helper}")
        content = helper.read_bytes()
        require(content.startswith(b"\x7fELF") and b"SUID_FIXTURE_ONLY=BENIGN_IDENTITY_REPORT" in content,
                "Expected the dedicated synthetic ELF helper")
        print(f"PASS {device[1]}: locked non-root account, warning, ground truth and synthetic ELF helper", flush=True)


def verify_guest(device, timeout):
    firmware = f"{device}-{SLUG}"
    environment = dict(os.environ, FIRMWARE=firmware, QEMU_PERSIST="0")
    master, slave = pty.openpty()
    transcript = bytearray()
    process = None
    log_path = Path(tempfile.gettempdir()) / f"iotbench-suid-{device}-qemu.log"
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
        # Only fixed benign commands are used by this root-console harness.
        # setpriv directly executes the helper after switching to UID/GID 993.
        command = (
            f"stat -c 'SUID_METADATA=%u:%g:%a' {HELPER}; "
            f"grep -Fx 'DEVICE_CLASS=\"{device}\"' /etc/iotbench/device.conf; "
            "printf '\\nSUID_DEVICE_EXIT=%s\\n' \"$?\"; "
            f"setpriv --reuid=993 --regid=993 --clear-groups {HELPER}; "
            "printf '\\nSUID_VALID_EXIT=%s\\n' \"$?\"; "
            f"setpriv --reuid=993 --regid=993 --clear-groups {HELPER} unexpected-argument; "
            "printf '\\nSUID_ARGUMENT_EXIT=%s\\n' \"$?\"; "
            "printf '\\nSUID_CHECKS_END\\n'\n"
        )
        os.write(master, command.encode())
        wait_for(b"\r\nSUID_CHECKS_END\r")
        output = transcript.replace(b"\r", b"")
        for line in ("SUID_METADATA=0:0:4755", "SUID_DEVICE_EXIT=0", "SUID_VALID_EXIT=0",
                     "SUID_ARGUMENT_EXIT=2", "SUID_FIXTURE_ONLY=BENIGN_IDENTITY_REPORT",
                     "REAL_UID=993", "EFFECTIVE_UID=0", "REAL_GID=993", "EFFECTIVE_GID=993"):
            require(re.search(rb"(?m)^" + re.escape(line.encode()) + rb"$", output),
                    f"Expected guest result missing: {line}")
        print(f"PASS {firmware}: root:root 4755, non-root real UID, root effective UID, argument rejection; log {log_path}", flush=True)
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
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--image", type=Path, help="offline ext4 or ext4.zst image inspection")
    selection.add_argument("--device", choices=DEVICES, help="boot and verify one exported device")
    selection.add_argument("--all", action="store_true", help="boot every device sequentially")
    parser.add_argument("--debugfs", default="debugfs", help="debugfs executable for --image")
    parser.add_argument("--timeout", type=int, default=150, help="seconds per guest console step")
    arguments = parser.parse_args()
    if arguments.image:
        verify_image(arguments.image, arguments.debugfs)
    else:
        for device in DEVICES if arguments.all else [arguments.device]:
            verify_guest(device, arguments.timeout)


if __name__ == "__main__":
    main()
