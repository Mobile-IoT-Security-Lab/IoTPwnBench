#!/usr/bin/env python3
"""Verify Java JAR SQL-injection firmware locally, offline, or in disposable QEMU.

Python standard library only. Offline inspection never mounts or executes the
firmware. Runtime testing uses the existing local serial-console harness.
"""

import argparse
import hashlib
import io
import zipfile
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
SLUG = "cwe089-java-sql-injection"
JAR = "/usr/share/iotbench/java-sql-injection/fixture-db-query.jar"
DATA = "/usr/share/iotbench/java-sql-injection"
WARNING = ("INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — "
           "LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def render(source):
    return source.replace("@DATADIR@", "/usr/share").replace("@LIBDIR@", "/usr/lib")


SOURCE = LAYER / "recipes-vulns" / SLUG / "files"
PUBLIC = "public|SYNTHETIC_PUBLIC_FIXTURE_DATA\n"
BOTH = PUBLIC + "internal|SYNTHETIC_INTERNAL_FIXTURE_DATA\n"
INJECTION = "public' OR '1'='1"


def verify_jar(blob):
    with zipfile.ZipFile(io.BytesIO(blob)) as jar:
        manifest = jar.read("META-INF/MANIFEST.MF").decode()
        require("Main-Class: org.iotbench.fixture.FixtureDbQuery\r\n" in manifest,
                "Missing executable JAR entry point")
        require("Class-Path: ../../java/iotbench-sqlite-jdbc.jar\r\n" in manifest,
                "Missing firmware JDBC Class-Path")
        bytecode = jar.read("org/iotbench/fixture/FixtureDbQuery.class")
        require(bytecode[:4] == b"\xca\xfe\xba\xbe", "Missing real Java bytecode")
        require(int.from_bytes(bytecode[6:8], "big") == 61, "Expected Java 17 class format")
        for symbol in (b"java/sql/DriverManager", b"java/sql/Statement", b"executeQuery",
                       b"createStatement", b"getConnection", b"java/sql/ResultSet",
                       b"SELECT record_name, record_value FROM fixture_records ",
                       b"WHERE record_name = '", b"open_mode", b"enable_load_extension", b"isReadOnly"):
            require(symbol in bytecode, f"Missing Java JDBC ground-truth reference: {symbol!r}")
        require(b"prepareStatement" not in bytecode, "Fixture unexpectedly parameterizes SQL")
        config = jar.read("fixture.properties").decode()
        require(f"database.url=jdbc:sqlite:file:{DATA}/fixture.db?mode=ro&immutable=1\n" in config,
                "Unexpected database URL or missing read-only configuration")
        require("driver.path=/usr/lib\n" in config, "Unexpected native JDBC path")


def verify_database(path):
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        require(db.execute("PRAGMA integrity_check").fetchall() == [("ok",)], "Database integrity")
        require(db.execute("SELECT name FROM sqlite_schema WHERE type='table'").fetchall()
                == [("fixture_records",)], "Unexpected database tables")
        require(db.execute("SELECT * FROM fixture_records ORDER BY id").fetchall() == [
            (1, "public", "SYNTHETIC_PUBLIC_FIXTURE_DATA", "public"),
            (2, "internal", "SYNTHETIC_INTERNAL_FIXTURE_DATA", "internal")], "Unexpected records")


def verify_image(path, debugfs):
    require(path.is_file(), f"Image not found: {path}")
    require(shutil.which(debugfs), f"debugfs not found: {debugfs}")
    with tempfile.TemporaryDirectory(prefix="iotbench-java-image-") as temporary:
        image = path.resolve()
        if path.suffix == ".zst":
            image = Path(temporary) / "rootfs.ext4"
            subprocess.run(["zstd", "-q", "-d", str(path), "-o", str(image)], check=True)

        def inspect(operation, name):
            result = subprocess.run([debugfs, "-R", f"{operation} {name}", str(image)],
                                    capture_output=True, check=True)
            require(b"File not found" not in result.stderr, f"Missing image path: {name}")
            return result.stdout

        def mode(name, expected):
            info = inspect("stat", name).decode()
            permissions = re.search(r"Mode:\s+([0-7]+)\b", info)
            owner = re.search(r"User:\s+(\d+)\s+Group:\s+(\d+)\b", info)
            require(permissions and owner and int(permissions[1], 8) == expected
                    and int(owner[1]) == int(owner[2]) == 0, f"Unexpected permissions: {name}")

        mode(JAR, 0o644)
        mode(DATA + "/fixture.db", 0o444)
        blob = inspect("cat", JAR)
        verify_jar(blob)
        for name in ("FixtureDbQuery.java", "schema.sql", "NOTICE", "LICENSE",
                     "ground-truth.json", "test-guest.sh"):
            mode(DATA + "/" + name, 0o644)
            expected = (SOURCE / name).read_text()
            if name in ("ground-truth.json", "test-guest.sh"):
                expected = render(expected)
            require(inspect("cat", DATA + "/" + name).decode() == expected,
                    f"Installed asset differs from source: {name}")
        with zipfile.ZipFile(io.BytesIO(inspect("cat", "/usr/share/java/iotbench-sqlite-jdbc.jar"))) as driver:
            require("org/sqlite/JDBC.class" in driver.namelist(), "Missing JDBC driver")
            require(not any(n.startswith("org/sqlite/native/") for n in driver.namelist()),
                    "Foreign native library bundled in JDBC JAR")
        require(inspect("cat", "/usr/lib/libsqlitejdbc.so").startswith(b"\x7fELF"), "Missing JNI ELF")
        require(inspect("cat", "/usr/lib/jvm/bin/java").startswith(b"\x7fELF"), "Missing Java runtime")
        database = Path(temporary) / "fixture.db"
        database.write_bytes(inspect("cat", DATA + "/fixture.db"))
        verify_database(database)
        require(WARNING.encode() in inspect("cat", "/etc/motd"), "Missing login warning")
        identity = inspect("cat", "/etc/iotbench/device.conf").decode()
        device = re.search(r'^DEVICE_CLASS="([a-z]+)"$', identity, re.MULTILINE)
        require(device and device[1] in DEVICES, "Unsupported device identity")
        print(f"PASS {device[1]}: Java bytecode/JDBC flow, runtime, JNI, exact assets and synthetic database")
        print(f"PASS JAR SHA-256 {hashlib.sha256(blob).hexdigest()}; "
              f"database SHA-256 {hashlib.sha256(database.read_bytes()).hexdigest()}")


def verify_local(driver, java, javac):
    """Compile real JAR bytecode and exercise JDBC; the driver must be explicitly supplied."""
    require(driver.is_file(), f"SQLite JDBC JAR not found: {driver}")
    for device in DEVICES:
        recipe = LAYER / "recipes-images" / f"iotbench-{device}-{SLUG}.bb"
        require(recipe.is_file(), f"Missing fixture: {device}")
        text = recipe.read_text()
        require(f"require recipes-devices/{device}/device-{device}.inc" in text,
                f"Missing device profile: {device}")
        require(f'IOTBENCH_VULN_INSTALL = "{SLUG}"' in text, f"Wrong vulnerability: {device}")
    with tempfile.TemporaryDirectory(prefix="iotbench-java-local-") as temporary:
        base = Path(temporary)
        database = base / "fixture.db"
        with sqlite3.connect(database) as db:
            db.executescript((SOURCE / "schema.sql").read_text())
        verify_database(database)
        before = database.read_bytes()

        def build(source, output):
            classes = base / output
            classes.mkdir()
            source_path = base / "FixtureDbQuery.java"
            source_path.write_text(source)
            subprocess.run([javac, "--release", "17", "-encoding", "UTF-8", "-g", "-Xlint:all",
                            "-Werror", "-d", str(classes), str(source_path)], check=True)
            # Local driver contains its official host JNI; firmware uses cross-built JNI.
            (classes / "fixture.properties").write_text(
                f"database.url=jdbc:sqlite:file:{database}?mode=ro&immutable=1\n"
                f"driver.path={base}\n")
            artifact = base / (output + ".jar")
            with zipfile.ZipFile(artifact, "w") as jar:
                jar.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\r\n"
                             "Main-Class: org.iotbench.fixture.FixtureDbQuery\r\n"
                             f"Class-Path: {driver.resolve().as_uri()}\r\n\r\n")
                for entry in classes.rglob("*"):
                    if entry.is_file():
                        jar.write(entry, entry.relative_to(classes))
            return artifact

        def run(artifact, inputs, code, expected):
            result = subprocess.run([java, "-Xmx32m", "-jar", str(artifact), *inputs],
                                    capture_output=True, text=True, timeout=15)
            require(result.returncode == code and result.stdout == expected,
                    f"JAR lookup mismatch for {inputs!r}: {result.returncode}, {result.stdout!r}, {result.stderr!r}")
            require(WARNING in result.stderr, "Missing runtime warning")

        source = (SOURCE / "FixtureDbQuery.java").read_text()
        vulnerable = build(source, "vulnerable")
        for inputs, code, expected in [(["public"], 0, PUBLIC), (["unknown"], 0, ""),
                                       ([INJECTION], 0, BOTH), ([], 2, ""),
                                       (["public", "extra"], 2, ""), ([""], 2, ""),
                                       (["0" * 240], 0, ""), (["0" * 241], 2, ""),
                                       (["'"], 1, ""), (["$(printf harmless); ../synthetic-only"], 0, "")]:
            run(vulnerable, inputs, code, expected)
        print("PASS real Java JAR/JDBC normal and injected lookups, argument boundaries and SQL errors")
        # Independent negative control proves that the injection assertion depends
        # on concatenation. It exists only in this temporary test directory.
        corrected = source.replace("+ \"WHERE record_name = '\" + input + \"' ORDER BY id;\";",
                                   '+ "WHERE record_name = ? ORDER BY id;";')
        corrected = corrected.replace("Statement stmt = connection.createStatement()",
                                      "java.sql.PreparedStatement stmt = connection.prepareStatement(query)")
        corrected = corrected.replace("try (ResultSet rs = stmt.executeQuery(query)) {",
                                      "stmt.setString(1, input);\n                try (ResultSet rs = stmt.executeQuery()) {")
        require(corrected != source and 'WHERE record_name = ?' in corrected, "Control replacement failed")
        control = build(corrected, "corrected")
        run(control, ["public"], 0, PUBLIC)
        run(control, [INJECTION], 0, "")
        require(database.read_bytes() == before, "Database bytes changed")
        require(not any(base.glob("fixture.db-*")), "Unexpected SQLite journal sidecar")
        print(f"PASS temporary parameterized control rejects injection; database unchanged; {len(DEVICES)} device recipes")


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
                   "printf '\\nJAVA_SQL_INJECTION_CHECK_EXIT=%s\\n' \"$?\"\n")
        os.write(master, command.encode())
        wait_for(b"\r\nJAVA_SQL_INJECTION_CHECK_EXIT=")
        wait_for(b"\r\n")
        output = transcript.replace(b"\r", b"")
        # Bash's terminal integration may prefix the first PASS with an OSC
        # command marker. Preserve the raw log but strip markers for assertions.
        output = re.sub(rb"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)", b"", output)
        require(re.search(rb"(?m)^JAVA_SQL_INJECTION_CHECK_EXIT=0$", output), "Guest regression failed")
        require(len(re.findall(rb"(?m)^PASS ", output)) == 5, "Missing guest checks")
        print(f"PASS {firmware}: Java normal SELECT, injected SELECT, bounded input, "
              f"read-only unprivileged execution; log {log_path}", flush=True)
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
    selection.add_argument("--local", action="store_true", help="compile and run JAR plus corrected control")
    selection.add_argument("--image", type=Path, help="offline ext4 or ext4.zst inspection")
    selection.add_argument("--device", choices=DEVICES, help="boot and verify one device")
    selection.add_argument("--all", action="store_true", help="boot every device fixture sequentially")
    parser.add_argument("--jdbc-jar", type=Path, help="explicit official SQLite JDBC 3.53.4.0 JAR for --local")
    parser.add_argument("--java", default="java")
    parser.add_argument("--javac", default="javac")
    parser.add_argument("--debugfs", default="debugfs")
    parser.add_argument("--timeout", type=int, default=180)
    arguments = parser.parse_args()
    if arguments.local:
        if arguments.jdbc_jar is None:
            parser.error("--local requires --jdbc-jar")
        require(hashlib.sha256(arguments.jdbc_jar.read_bytes()).hexdigest() ==
                "bcb1f51e36f940867e83342f9efbf5968ac44a6bef4d397bb4af7b17b45cd2fb",
                "JDBC JAR differs from pinned dependency")
        verify_local(arguments.jdbc_jar, arguments.java, arguments.javac)
    elif arguments.image:
        verify_image(arguments.image, arguments.debugfs)
    else:
        for device in DEVICES if arguments.all else [arguments.device]:
            verify_guest(device, arguments.timeout)


if __name__ == "__main__":
    main()


