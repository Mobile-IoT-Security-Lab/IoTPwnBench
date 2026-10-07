#!/usr/bin/env python3
"""Inspect a Bash CWE-22 ext4 fixture offline or verify traversal in disposable QEMU.

Python standard library only. Offline inspection never mounts or executes the
firmware. Runtime testing uses the existing local serial-console harness.
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
SLUG = "cwe022-bash-path-traversal"
HELPER = "/usr/bin/iotbench-bash-read"
DATA = "/usr/share/iotbench/bash-path-traversal"
BUILTIN = "/usr/lib/iotbench/bash-path-traversal/fixture-confine.so"
JAIL = DATA + "/rootfs"
WARNING = ("INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — "
           "LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def render(source):
    return (source.replace("@DATADIR@", "/usr/share").replace("@LIBDIR@", "/usr/lib")
            .replace("@BINDIR@", "/usr/bin"))


def verify_image(path, debugfs):
    require(path.is_file(), f"Image not found: {path}")
    require(shutil.which(debugfs), f"debugfs not found: {debugfs}")
    with tempfile.TemporaryDirectory(prefix="iotbench-bash-traversal-") as temporary:
        image = path.resolve()
        if path.suffix == ".zst":
            image = Path(temporary) / "rootfs.ext4"
            subprocess.run(["zstd", "-q", "-d", str(path), "-o", str(image)], check=True)

        def inspect(operation, name):
            result = subprocess.run([debugfs, "-R", f"{operation} {name}", str(image)],
                                    capture_output=True, check=True)
            require(b"File not found" not in result.stderr, f"Missing image path: {name}")
            return result.stdout

        def text(operation, name):
            return inspect(operation, name).decode()

        def metadata(name):
            info = text("stat", name)
            mode = re.search(r"Mode:\s+([0-7]+)\b", info)
            owner = re.search(r"User:\s+(\d+)\s+Group:\s+(\d+)\b", info)
            kind = re.search(r"Type:\s+(\w+)", info)
            require(mode and owner and kind, f"Cannot parse inode: {name}")
            return kind[1], int(mode[1], 8), int(owner[1]), int(owner[2])

        for name in (HELPER, BUILTIN):
            require(metadata(name) == ("regular", 0o755, 0, 0),
                    f"Must be ordinary root:root 0755: {name}")
        source = LAYER / "recipes-vulns" / SLUG / "files"
        helper = text("cat", HELPER)
        require(helper == render((source / "iotbench-bash-read").read_text()),
                "Installed vulnerable Bash helper differs from source")
        require(helper.startswith("#!/bin/bash\n"), "Fixture must use actual Bash")
        require(text("cat", DATA + "/test-guest.sh") == render((source / "test-guest.sh").read_text()),
                "Guest verifier differs from source")
        require(text("cat", DATA + "/fixture-confine.c") == (source / "fixture-confine.c").read_text(),
                "Confinement source differs from source")
        builtin = inspect("cat", BUILTIN)
        require(builtin.startswith(b"\x7fELF") and JAIL.encode() in builtin
                and b"fixture_confine_struct" in builtin, "Missing fixed Bash confinement builtin")
        # Recursively inspect the whole jail: only root-owned directories and
        # the two exact synthetic regular files are permitted, with no mounts.
        actual_files = set()

        def check_tree(directory):
            require(metadata(directory) == ("directory", 0o755, 0, 0),
                    f"Unsafe jail directory: {directory}")
            listing = text("ls -p", directory)
            for line in listing.splitlines():
                if not line.strip():
                    continue
                fields = line.split("/")
                require(len(fields) >= 7, f"Cannot parse jail directory entry: {line}")
                name = fields[5]
                if name in (".", ".."):
                    continue
                child = directory + "/" + name
                kind, mode, uid, gid = metadata(child)
                if kind == "directory":
                    check_tree(child)
                else:
                    require((kind, mode, uid, gid) == ("regular", 0o644, 0, 0),
                            f"Unsafe jail entry: {child}")
                    actual_files.add(child)

        check_tree(JAIL)
        expected_files = {JAIL + DATA + "/data/public.txt", JAIL + DATA + "/internal/private-fixture.txt"}
        require(actual_files == expected_files, f"Unexpected accessible jail files: {actual_files}")
        for name, source_name in ((JAIL + DATA + "/data/public.txt", "public.txt"),
                                  (JAIL + DATA + "/internal/private-fixture.txt", "private-fixture.txt")):
            require(inspect("cat", name) == (source / source_name).read_bytes(),
                    f"Wrong synthetic fixture contents: {name}")
        for parent in ("/", "/usr", "/usr/bin", "/usr/lib", "/usr/lib/iotbench",
                       str(Path(BUILTIN).parent), "/usr/share", "/usr/share/iotbench", DATA):
            kind, mode, uid, gid = metadata(parent)
            require(kind == "directory" and uid == gid == 0 and not mode & 0o022,
                    f"Unsafe fixture ancestor: {parent}")
        truth = json.loads(text("cat", DATA + "/ground-truth.json"))
        expected = json.loads(render((source / "ground-truth.json").read_text()))
        require(truth == expected, "Ground-truth metadata differs from fixture")
        require(text("cat", DATA + "/NOTICE") == (source / "NOTICE").read_text()
                and WARNING in text("cat", "/etc/motd"), "Required warning missing")
        # update-alternatives installs /bin/bash as a symlink to bash.bash.
        interpreter = inspect("cat", "/bin/bash.bash")
        require(interpreter.startswith(b"\x7fELF"), "Actual Bash interpreter missing")
        identity = text("cat", "/etc/iotbench/device.conf")
        device = re.search(r'^DEVICE_CLASS="([a-z]+)"$', identity, re.MULTILINE)
        require(device and device[1] in DEVICES, "Unsupported device identity")
        print(f"PASS {device[1]}: exact Bash input-to-path-to-read fixture, two synthetic jail files, "
              "normal permissions, confinement builtin, warning and CWE-22 ground truth", flush=True)
        print(f"PASS helper SHA-256 {hashlib.sha256(helper.encode()).hexdigest()}; "
              f"builtin SHA-256 {hashlib.sha256(builtin).hexdigest()}", flush=True)


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
                   "printf '\\nBASH_TRAVERSAL_CHECK_EXIT=%s\\n' \"$?\"\n")
        os.write(master, command.encode())
        wait_for(b"\r\nBASH_TRAVERSAL_CHECK_EXIT=")
        wait_for(b"\r\n")
        output = transcript.replace(b"\r", b"")
        # Bash's terminal integration may prefix the first PASS with an OSC
        # command marker. Preserve the raw log but strip markers for assertions.
        output = re.sub(rb"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)", b"", output)
        require(re.search(rb"(?m)^BASH_TRAVERSAL_CHECK_EXIT=0$", output), "Guest regression failed")
        require(len(re.findall(rb"(?m)^PASS ", output)) == 5, "Missing guest checks")
        print(f"PASS {firmware}: public read, Bash ../ traversal, literal-path checks, "
              f"synthetic-only confinement and normal permissions; log {log_path}", flush=True)
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
