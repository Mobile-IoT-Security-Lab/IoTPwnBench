#!/usr/bin/env python3
"""Inspect native C SQL-injection firmware offline or test it in disposable QEMU.

Python standard library only. Offline inspection never mounts or executes the
firmware. Runtime testing uses the existing local serial-console harness.
"""

import argparse
import hashlib
import os
from pathlib import Path
import pty
import re
import select
import shutil
import sqlite3
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / "meta-iotbench"
if not LAYER.is_dir():
    LAYER = Path("/opt/yocto/layers/meta-iotbench")
DEVICES = sorted(p.parent.name for p in (LAYER / "recipes-devices").glob("*/device-*.inc"))
SLUG = "cwe089-c-sql-injection"
HELPER = "/usr/bin/fixture-db-query"
DATA = "/usr/share/iotbench/c-sql-injection"
WARNING = ("INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — "
           "LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def render(source):
    return (source.replace("@DATADIR@", "/usr/share").replace("@SYSCONFDIR@", "/etc")
            .replace("@BINDIR@", "/usr/bin"))


def verify_image(path, debugfs):
    require(path.is_file(), f"Image not found: {path}")
    require(shutil.which(debugfs), f"debugfs not found: {debugfs}")
    with tempfile.TemporaryDirectory(prefix="iotbench-c-sql-") as temporary:
        image = path.resolve()
        if path.suffix == ".zst":
            image = Path(temporary) / "rootfs.ext4"
            subprocess.run(["zstd", "-q", "-d", str(path), "-o", str(image)], check=True)

        def inspect(operation, name):
            result = subprocess.run([debugfs, "-R", f"{operation} {name}", str(image)],
                                    capture_output=True, check=True)
            require(b"File not found" not in result.stderr, f"Missing image path: {name}")
            return result.stdout

        def metadata(name):
            info = inspect("stat", name).decode()
            mode = re.search(r"Mode:\s+([0-7]+)\b", info)
            owner = re.search(r"User:\s+(\d+)\s+Group:\s+(\d+)\b", info)
            kind = re.search(r"Type:\s+(\w+)", info)
            require(mode and owner and kind, f"Cannot parse inode: {name}")
            return kind[1], int(mode[1], 8), int(owner[1]), int(owner[2])

        require(metadata(HELPER) == ("regular", 0o755, 0, 0), "Helper must be root:root 0755")
        require(metadata(DATA + "/fixture.db") == ("regular", 0o444, 0, 0),
                "Database must be root:root 0444")
        for parent in ("/", "/usr", "/usr/bin", "/usr/share", "/usr/share/iotbench", DATA):
            kind, mode, uid, gid = metadata(parent)
            require(kind == "directory" and uid == gid == 0 and not mode & 0o022,
                    f"Unsafe fixture ancestor: {parent}")
        source = LAYER / "recipes-vulns" / SLUG / "files"
        for name in ("fixture-db-query.c", "schema.sql", "NOTICE", "LICENSE",
                     "ground-truth.json", "test-guest.sh"):
            require(metadata(DATA + "/" + name) == ("regular", 0o644, 0, 0),
                    f"Unsafe fixture asset: {name}")
            expected = (source / name).read_text()
            if name in ("ground-truth.json", "test-guest.sh"):
                expected = render(expected)
            require(inspect("cat", DATA + "/" + name).decode() == expected,
                    f"Installed asset differs from source: {name}")
        helper = inspect("cat", HELPER)
        require(helper.startswith(b"\x7fELF"), "Helper must be a native ELF executable")
        for symbol in (b"snprintf", b"sqlite3_open_v2", b"sqlite3_prepare_v2", b"sqlite3_step",
                       b"sqlite3_column_text", b"sqlite3_finalize", b"sqlite3_close"):
            require(symbol in helper, f"Missing expected native API reference: {symbol!r}")
        require((DATA + "/fixture.db").encode() in helper, "Missing fixed database path")
        require(b"sqlite3_bind_" not in helper, "Fixture unexpectedly binds SQL parameters")
        database_bytes = inspect("cat", DATA + "/fixture.db")
        database = Path(temporary) / "fixture.db"
        database.write_bytes(database_bytes)
        # Inspect only the extracted synthetic database; never execute firmware on the host.
        connection = sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)
        try:
            require(connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)],
                    "Synthetic database failed integrity check")
            tables = connection.execute(
                "SELECT name FROM sqlite_schema WHERE type='table' ORDER BY name").fetchall()
            require(tables == [("fixture_records",)], "Unexpected synthetic database tables")
            columns = connection.execute("PRAGMA table_info(fixture_records)").fetchall()
            require([(row[1], row[2]) for row in columns] ==
                    [("id", "INTEGER"), ("record_name", "TEXT"),
                     ("record_value", "TEXT"), ("visibility", "TEXT")], "Unexpected schema")
            require(connection.execute("SELECT * FROM fixture_records ORDER BY id").fetchall() == [
                (1, "public", "SYNTHETIC_PUBLIC_FIXTURE_DATA", "public"),
                (2, "internal", "SYNTHETIC_INTERNAL_FIXTURE_DATA", "internal")],
                "Synthetic records differ from ground truth")
        finally:
            connection.close()
        require(WARNING.encode() in inspect("cat", "/etc/motd"), "Required login warning missing")
        identity = inspect("cat", "/etc/iotbench/device.conf").decode()
        device = re.search(r'^DEVICE_CLASS="([a-z]+)"$', identity, re.MULTILINE)
        require(device and device[1] in DEVICES, "Unsupported device identity")
        print(f"PASS {device[1]}: native C SQLite APIs, exact source/assets, synthetic schema/records, "
              "ordinary permissions, warning and CWE-89 ground truth", flush=True)
        print(f"PASS ELF SHA-256 {hashlib.sha256(helper).hexdigest()}; "
              f"database SHA-256 {hashlib.sha256(database_bytes).hexdigest()}", flush=True)


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
                   "printf '\\nC_SQL_INJECTION_CHECK_EXIT=%s\\n' \"$?\"\n")
        os.write(master, command.encode())
        wait_for(b"\r\nC_SQL_INJECTION_CHECK_EXIT=")
        wait_for(b"\r\n")
        output = transcript.replace(b"\r", b"")
        # Bash's terminal integration may prefix the first PASS with an OSC
        # command marker. Preserve the raw log but strip markers for assertions.
        output = re.sub(rb"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)", b"", output)
        require(re.search(rb"(?m)^C_SQL_INJECTION_CHECK_EXIT=0$", output), "Guest regression failed")
        require(len(re.findall(rb"(?m)^PASS ", output)) == 6, "Missing guest checks")
        print(f"PASS {firmware}: normal SELECT, injected SELECT, bounded input, "
              f"synthetic-only SQL scope, read-only unprivileged execution; log {log_path}", flush=True)
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
