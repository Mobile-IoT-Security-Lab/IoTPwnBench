#!/usr/bin/env python3
"""Validate CWE-190 locally, inspect exported firmware, or boot disposable QEMU.

--local builds a separate host test executable. --sanitize additionally requires
Clang's unsigned-integer-overflow diagnostic and a corrected temporary control.
--image reads ext4 via debugfs; it never executes firmware on the host.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import pty
import random
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
SLUG = "cwe190-integer-overflow"
HELPER = "/usr/bin/fixture-batch-size"
DATA = "/usr/share/iotbench/integer-overflow"
SOURCE = LAYER / "recipes-vulns" / SLUG / "files"
WARNING = ("INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — "
           "LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT")
MACHINES = {"qemuarm64": (2, 1, 183), "qemuarm": (1, 1, 40),
            "qemux86-64": (2, 1, 62), "qemux86": (1, 1, 3), "qemumips": (1, 2, 8)}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def render(source):
    return (source.replace("@DATADIR@", "/usr/share").replace("@SYSCONFDIR@", "/etc")
            .replace("@BINDIR@", "/usr/bin"))


def expected_output(count):
    # Python's exact arithmetic is the independent oracle, never target code.
    total = (count * 1024) % (1 << 32)
    decision = "accepted" if total <= 4096 else "exceeds capacity"
    return (f"record_count = {count}\nrecord_size = 1024\ntotal_size = {total}\n"
            f"max_capacity = 4096\nSynthetic batch {decision}\n")


def verify_integration():
    truth = json.loads((SOURCE / "ground-truth.json").read_text())
    lines = (SOURCE / "fixture-batch-size.c").read_text().splitlines()
    for key, expression in (
        ("input_line", "if (argc != 2 || !parse_record_count(argv[1], &record_count)) {"),
        ("conversion_line", "parsed = strtoumax(input, &end, 10);"),
        ("arithmetic_line", "return record_count * record_size;"),
        ("assignment_line", "uint32_t total_size = calculate_total(record_count, record_size);"),
        ("decision_line", "if (total_size <= max_capacity) {"),
    ):
        require(lines[truth[key] - 1].strip() == expression, f"Stale source location: {key}")
    require(truth["label"] == "Vulnerable C Binaries — Integer Overflow" and
            truth["cwe"] == "CWE-190" and truth["maximum"] == (1 << 32) - 1,
            "Incorrect ground truth")
    recipes = LAYER / "recipes-images"
    require(DEVICES and DEVICES == sorted(p.name.removeprefix("iotbench-").removesuffix(
        f"-{SLUG}.bb") for p in recipes.glob(f"iotbench-*-{SLUG}.bb")),
        "Image recipes must cover every supported device exactly once")
    for device in DEVICES:
        recipe = (recipes / f"iotbench-{device}-{SLUG}.bb").read_text()
        for expected in ("require recipes-images/iotbench-image.inc",
                         f"require recipes-devices/{device}/device-{device}.inc",
                         "require recipes-images/iotbench-integer-overflow.inc",
                         f'IOTBENCH_VULN_INSTALL = "{SLUG}"', 'IOTBENCH_CWE = "CWE-190"', WARNING):
            require(expected in recipe, f"Incorrect integration: {device}: {expected}")
    print(f"PASS source locations, CWE-190 ground truth and all {len(DEVICES)} device recipes", flush=True)


def verify_local(cc, sanitize, clang):
    verify_integration()
    with tempfile.TemporaryDirectory(prefix="iotbench-integer-local-") as temporary:
        executable = Path(temporary) / "fixture-batch-size"
        source = SOURCE / "fixture-batch-size.c"
        flags = ["-std=c99", "-O0", "-g", "-Wall", "-Wextra", "-Werror"]
        subprocess.run([cc, *flags, str(source), "-o", str(executable)], check=True, timeout=60)

        def run(arguments, binary=executable):
            return subprocess.run([str(binary), *arguments], capture_output=True, text=True,
                                  timeout=5)

        rng = random.Random(190)
        counts = [0, 1, 2, 4, 5, 4194303, 4194304, 4194305, 8388608, (1 << 32) - 1]
        counts += [rng.randrange(1 << 32) for _ in range(64)]
        for count in counts:
            result = run([str(count)])
            require(result.returncode == 0 and result.stdout == expected_output(count),
                    f"Wrong numerical result/decision for {count}: {result}")
            require(result.stderr == WARNING + "\n", "Missing or unexpected stderr")
        for value in ("0002", "0000000000000000000000000000000002"):
            result = run([value])
            require(result.returncode == 0 and result.stdout == expected_output(2),
                    "Leading-zero decimal conversion failed")
        invalid = [[], ["2", "extra"]] + [[item] for item in (
            "", "-1", "+2", " 2", "2 ", "2\n", "2x", "1.5", "0x2", "2_0", "٢",
            "4294967296", "18446744073709551616", "9" * 1000, "$(printf harmless); ../fixture")]
        for arguments in invalid:
            result = run(arguments)
            require(result.returncode == 2 and not result.stdout and WARNING in result.stderr,
                    f"Invalid input not rejected correctly: {arguments!r}: {result}")
        require(4194304 * 1024 == 4294967296 and 4294967296 > 4096,
                "Incorrect exact mathematical overflow witness")
        print(f"PASS host C build: {len(counts)} exact arithmetic/decision cases, decimal aliases, "
              "strict malformed/range checks; 4194304 * 1024 wraps to 0 and is accepted", flush=True)

        if sanitize:
            diagnostic = Path(temporary) / "diagnostic"
            instrumentation = ["-fsanitize=unsigned-integer-overflow",
                               "-fno-sanitize-recover=unsigned-integer-overflow"]
            subprocess.run([clang, *flags, *instrumentation, str(source), "-o", str(diagnostic)],
                           check=True, timeout=60)
            normal = run(["2"], diagnostic)
            require(normal.returncode == 0 and normal.stdout == expected_output(2) and
                    "runtime error" not in normal.stderr, "Diagnostic normal-input check failed")
            overflow = run(["4194304"], diagnostic)
            line = json.loads((SOURCE / "ground-truth.json").read_text())["arithmetic_line"]
            require(overflow.returncode != 0 and f"fixture-batch-size.c:{line}:" in overflow.stderr
                    and "unsigned integer overflow" in overflow.stderr
                    and "4194304 * 1024" in overflow.stderr, "Missing exact unsigned overflow diagnostic")
            print(overflow.stderr.strip(), flush=True)
            # Correct only a temporary test control. The image's source is unchanged.
            safe = Path(temporary) / "safe-control.c"
            original = source.read_text()
            assignment = "    uint32_t total_size = calculate_total(record_count, record_size);"
            safe.write_text(original.replace(assignment,
                "    if (record_count > UINT32_MAX / record_size) { return 2; }\n" + assignment, 1))
            subprocess.run([clang, *flags, *instrumentation, str(safe), "-o", str(diagnostic)],
                           check=True, timeout=60)
            for argument, expected_status in (("2", 0), ("4194304", 2), ("4294967295", 2)):
                control = run([argument], diagnostic)
                require(control.returncode == expected_status and "runtime error" not in control.stderr,
                        "Corrected temporary control failed")
                require(control.stdout == (expected_output(2) if expected_status == 0 else ""),
                        "Incorrect temporary control output")
            print("PASS Clang unsigned-overflow diagnostic at the multiplication; normal input and "
                  "corrected temporary control have no diagnostic (firmware remains vulnerable)", flush=True)


def verify_image(path, debugfs, machine, objdump):
    verify_integration()
    require(path.is_file(), f"Image not found: {path}")
    require(shutil.which(debugfs), f"debugfs not found: {debugfs}")
    with tempfile.TemporaryDirectory(prefix="iotbench-integer-image-") as temporary:
        image = path.resolve()
        if path.suffix == ".zst":
            image = Path(temporary) / "rootfs.ext4"
            subprocess.run(["zstd", "-q", "-d", str(path), "-o", str(image)],
                           check=True, timeout=120)

        def inspect(operation, name):
            result = subprocess.run([debugfs, "-R", f"{operation} {name}", str(image)],
                                    capture_output=True, check=True, timeout=30)
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
        for parent in ("/", "/usr", "/usr/bin", "/usr/share", "/usr/share/iotbench", DATA):
            kind, mode, uid, gid = metadata(parent)
            require(kind == "directory" and uid == gid == 0 and not mode & 0o022,
                    f"Unsafe fixture ancestor: {parent}")
        for name in ("fixture-batch-size.c", "NOTICE", "LICENSE", "ground-truth.json", "test-guest.sh"):
            require(metadata(DATA + "/" + name) == ("regular", 0o644, 0, 0),
                    f"Incorrect asset permissions: {name}")
            expected = (SOURCE / name).read_text()
            if name in ("ground-truth.json", "test-guest.sh"):
                expected = render(expected)
            require(inspect("cat", DATA + "/" + name).decode() == expected,
                    f"Installed asset differs from source: {name}")
        helper = inspect("cat", HELPER)
        require(helper.startswith(b"\x7fELF"), "Helper must be a native ELF executable")
        byteorder = "little" if helper[5] == 1 else "big"
        require((helper[4], helper[5], int.from_bytes(helper[18:20], byteorder)) == MACHINES[machine],
                f"ELF architecture does not match {machine}")
        for marker in (b"parse_record_count", b"calculate_total", b"strtou", b"printf",
                       b"Synthetic batch accepted", b"Synthetic batch exceeds capacity", WARNING.encode()):
            require(marker in helper, f"Missing native arithmetic/input/decision marker: {marker!r}")
        require(b"__ubsan" not in helper and b"__asan" not in helper,
                "Instrumentation must not be installed in the firmware helper")
        binary = Path(temporary) / "fixture-batch-size"
        binary.write_bytes(helper)
        disassembly = subprocess.run([objdump, "-d", str(binary)], capture_output=True,
                                     text=True, check=True, timeout=30).stdout
        require("<calculate_total>:" in disassembly and "<main>:" in disassembly,
                "Arithmetic and main must remain recognizable in the executable")
        main = disassembly.split("<main>:", 1)[1].split("\n\n", 1)[0]
        arithmetic = disassembly.split("<calculate_total>:", 1)[1].split("\n\n", 1)[0]
        require("<calculate_total>" in main and "<parse_record_count>" in main,
                "Native main must call the input parser and arithmetic function")
        pattern = {"qemuarm64": r"\bmul\s+w\d+,\s*w\d+,\s*w\d+",
                   "qemuarm": r"\bmul(?:s|\.w)?\s+",
                   "qemux86-64": r"\bimul\s+[^\n]*%e\w+",
                   "qemux86": r"\bimul\s+[^\n]*%e\w+",
                   "qemumips": r"\bmult?u?\s+"}[machine]
        operation = re.search(pattern, arithmetic)
        require(operation, "Expected native 32-bit multiplication missing from calculate_total")
        require(WARNING.encode() in inspect("cat", "/etc/motd"), "Required image warning missing")
        identity = inspect("cat", "/etc/iotbench/device.conf").decode()
        device = re.search(r'^DEVICE_CLASS="([a-z]+)"$', identity, re.MULTILINE)
        require(device and device[1] in DEVICES, "Unsupported device identity")
        if path.name.startswith("iotbench-"):
            expected_name = f"iotbench-{device[1]}-{SLUG}-{machine}.rootfs.ext4"
            require(path.name in (expected_name, expected_name + ".zst"),
                    "Exported image name does not match the installed device profile")
        profile = LAYER / "recipes-devices" / device[1] / "files"
        for name in ("device.conf", "peripherals.conf"):
            require(inspect("cat", "/etc/iotbench/" + name) == (profile / name).read_bytes(),
                    f"Installed device profile differs from source: {name}")
        print(f"PASS {device[1]}: {machine} ELF, parser/arithmetic calls, native {operation[0]}, "
              "exact source/assets, profile, ordinary permissions and image warning", flush=True)
        print(f"PASS ELF SHA-256 {hashlib.sha256(helper).hexdigest()}", flush=True)


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
                   "printf '\\nINTEGER_OVERFLOW_CHECK_EXIT=%s\\n' \"$?\"\n")
        os.write(master, command.encode())
        wait_for(b"\r\nINTEGER_OVERFLOW_CHECK_EXIT=")
        wait_for(b"\r\n")
        output = transcript.replace(b"\r", b"")
        # Bash's terminal integration may prefix the first PASS with an OSC
        # command marker. Preserve the raw log but strip markers for assertions.
        output = re.sub(rb"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)", b"", output)
        require(re.search(rb"(?m)^INTEGER_OVERFLOW_CHECK_EXIT=0$", output), "Guest regression failed")
        require(len(re.findall(rb"(?m)^PASS ", output)) == 6, "Missing guest checks")
        print(f"PASS {firmware}: normal arithmetic, uint32_t wrap, incorrect capacity decision, "
              f"strict parsing and unprivileged execution; log {log_path}", flush=True)
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
    selection.add_argument("--local", action="store_true", help="host C build and numerical/parser checks")
    selection.add_argument("--image", type=Path, help="offline ext4 or ext4.zst inspection")
    selection.add_argument("--device", choices=DEVICES, help="boot and verify one device")
    selection.add_argument("--all", action="store_true", help="boot all device fixtures sequentially")
    parser.add_argument("--cc", default="cc", help="host compiler for --local")
    parser.add_argument("--sanitize", action="store_true", help="require Clang unsigned-overflow diagnostic with --local")
    parser.add_argument("--clang", default="clang", help="Clang compiler for --sanitize")
    parser.add_argument("--debugfs", default="debugfs", help="debugfs path for --image")
    parser.add_argument("--objdump", default="objdump", help="matching target objdump for --image")
    parser.add_argument("--machine", choices=MACHINES, default=os.environ.get("YOCTO_MACHINE", "qemuarm64"),
                        help="expected ELF architecture for --image")
    parser.add_argument("--timeout", type=int, default=150, help="seconds per console step")
    arguments = parser.parse_args()
    if arguments.sanitize and not arguments.local:
        parser.error("--sanitize requires --local")
    if arguments.local:
        verify_local(arguments.cc, arguments.sanitize, arguments.clang)
    elif arguments.image:
        verify_image(arguments.image, arguments.debugfs, arguments.machine, arguments.objdump)
    else:
        for device in DEVICES if arguments.all else [arguments.device]:
            verify_guest(device, arguments.timeout)


if __name__ == "__main__":
    main()
