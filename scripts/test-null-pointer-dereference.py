#!/usr/bin/env python3
"""Verify CWE-476 source with GCC, inspect firmware, or boot a disposable QEMU guest.

Use --static inside the existing Linux builder (GCC -fanalyzer required).
Offline image inspection never executes the firmware on the host.
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
SLUG = "cwe476-null-pointer-dereference"
HELPER = "/usr/bin/fixture-device-info"
DATA = "/usr/share/iotbench/null-pointer-dereference"
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


def verify_static(cc):
    """Require a real interprocedural CWE-476 finding, plus a safe negative control."""
    truth = json.loads((SOURCE / "ground-truth.json").read_text())
    source = (SOURCE / truth["source"]).read_text()
    lines = source.splitlines()
    for key, expression in (("input_line", "const char *input = argv[1];"),
                            ("null_return_line", "return NULL;"),
                            ("assignment_line", truth["nullable_assignment"]),
                            ("dereference_line", 'printf("Record ID: %d\\n", record->id);')):
        require(lines[truth[key] - 1].strip() == expression, f"Stale source location: {key}")
    require(truth["cwe"] == "CWE-476" and truth["label"] ==
            "Vulnerable C Binaries — Null Pointer Dereference", "Incorrect ground truth")
    require(sorted(DEVICES) == sorted(p.name.removeprefix("iotbench-").removesuffix(
        f"-{SLUG}.bb") for p in (LAYER / "recipes-images").glob(f"iotbench-*-{SLUG}.bb")),
        "Image recipes must cover every supported device exactly once")
    for device in DEVICES:
        recipe = (LAYER / "recipes-images" / f"iotbench-{device}-{SLUG}.bb").read_text()
        require(f"require recipes-devices/{device}/device-{device}.inc" in recipe and
                f'IOTBENCH_VULN_INSTALL = "{SLUG}"' in recipe and WARNING in recipe,
                f"Incorrect device integration: {device}")

    with tempfile.TemporaryDirectory(prefix="iotbench-null-static-") as temporary:
        def analyze(name, text):
            path = Path(temporary) / name
            path.write_text(text)
            result = subprocess.run([cc, "-std=c99", "-O0", "-Wall", "-Wextra", "-fanalyzer",
                                     "-fdiagnostics-format=json", "-c", str(path), "-o",
                                     str(Path(temporary) / "fixture.o")],
                                    capture_output=True, text=True, timeout=60)
            require(result.returncode == 0, f"GCC compilation failed: {result.stderr}")
            return json.loads(result.stderr)

        findings = analyze("fixture-device-info.c", source)
        matches = [item for item in findings if item.get("metadata", {}).get("cwe") == 476
                   and item.get("option") == "-Wanalyzer-null-dereference"]
        require(len(matches) == 1, f"Expected one CWE-476 diagnostic, got {findings}")
        finding = matches[0]
        require(finding["locations"][0]["caret"]["line"] == truth["dereference_line"],
                "Analyzer sink differs from ground truth")
        path_lines = {event["location"]["line"] for event in finding["path"]}
        require({truth[key] for key in ("input_line", "null_return_line", "assignment_line",
                                       "dereference_line")} <= path_lines,
                "Analyzer did not establish the input/NULL/return/dereference path")
        print(json.dumps(finding, ensure_ascii=False, indent=2), flush=True)
        # Only this temporary negative control is corrected; firmware stays vulnerable.
        safe = source.replace('    /* INTENTIONALLY VULNERABLE',
                              '    if (record == NULL) { return 1; }\n\n'
                              '    /* INTENTIONALLY VULNERABLE', 1)
        require(not any(item.get("metadata", {}).get("cwe") == 476
                        for item in analyze("safe-control.c", safe)),
                "Correctly checked negative control still reports CWE-476")
    print("PASS GCC analyzer: argv input -> lookup -> NULL return -> record -> unchecked "
          "record->id (CWE-476); corrected temporary control has no CWE-476", flush=True)
    print(f"PASS source locations, ground truth and all {len(DEVICES)} device recipes", flush=True)


def verify_image(path, debugfs, machine, objdump):
    require(path.is_file(), f"Image not found: {path}")
    require(shutil.which(debugfs), f"debugfs not found: {debugfs}")
    with tempfile.TemporaryDirectory(prefix="iotbench-null-image-") as temporary:
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

        for executable in (HELPER, DATA + "/test-null-dereference"):
            require(metadata(executable) == ("regular", 0o755, 0, 0),
                    f"Executable must be root:root 0755: {executable}")
        for name in ("fixture-device-info.c", "test-null-dereference.c", "NOTICE", "LICENSE",
                     "ground-truth.json", "test-guest.sh"):
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
        for marker in (b"lookup_record", b"records", b"strcmp", b"printf",
                       b"SYNTHETIC_PUBLIC_FIXTURE_DATA", b"SYNTHETIC_STATUS_FIXTURE_DATA",
                       WARNING.encode()):
            require(marker in helper, f"Missing native lookup/data marker: {marker!r}")
        require(b"__ubsan" not in helper and b"__asan" not in helper,
                "Instrumentation must not be installed in the firmware helper")
        binary = Path(temporary) / "fixture-device-info"
        binary.write_bytes(helper)
        # Use a matching objdump (native builder works for the default aarch64 target).
        disassembly = subprocess.run([objdump, "-d", str(binary)], capture_output=True,
                                     text=True, check=True, timeout=30).stdout
        require("<lookup_record>:" in disassembly and "<main>:" in disassembly,
                "Lookup and main must remain separately recognizable in the executable")
        main = disassembly.split("<main>:", 1)[1].split("\n\n", 1)[0]
        require("<lookup_record>" in main, "Native main must still call the record lookup")
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
        print(f"PASS {device[1]}: {machine} native ELF, lookup call, synthetic records, exact "
              "source/assets/ground truth, device profile, permissions and image warning", flush=True)
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
                   "printf '\\nNULL_POINTER_CHECK_EXIT=%s\\n' \"$?\"\n")
        os.write(master, command.encode())
        wait_for(b"\r\nNULL_POINTER_CHECK_EXIT=")
        wait_for(b"\r\n")
        output = transcript.replace(b"\r", b"")
        # Bash's terminal integration may prefix the first PASS with an OSC
        # command marker. Preserve the raw log but strip markers for assertions.
        output = re.sub(rb"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)", b"", output)
        require(re.search(rb"(?m)^NULL_POINTER_CHECK_EXIT=0$", output), "Guest regression failed")
        require(len(re.findall(rb"(?m)^PASS ", output)) == 5, "Missing guest checks")
        print(f"PASS {firmware}: valid records, argument validation, kernel-confirmed NULL "
              f"dereference, unprivileged execution and core suppression; log {log_path}", flush=True)
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
    selection.add_argument("--static", action="store_true", help="GCC source analysis and recipe checks")
    selection.add_argument("--image", type=Path, help="offline ext4 or ext4.zst inspection")
    selection.add_argument("--device", choices=DEVICES, help="boot and verify one device")
    selection.add_argument("--all", action="store_true", help="boot all device fixtures sequentially")
    parser.add_argument("--cc", default="gcc", help="GCC with -fanalyzer for --static")
    parser.add_argument("--debugfs", default="debugfs", help="debugfs path for --image")
    parser.add_argument("--objdump", default="objdump", help="matching target objdump for --image")
    parser.add_argument("--machine", choices=MACHINES, default=os.environ.get("YOCTO_MACHINE", "qemuarm64"),
                        help="expected ELF architecture for --image")
    parser.add_argument("--timeout", type=int, default=150, help="seconds per console step")
    arguments = parser.parse_args()
    if arguments.static:
        verify_static(arguments.cc)
    elif arguments.image:
        verify_image(arguments.image, arguments.debugfs, arguments.machine, arguments.objdump)
    else:
        for device in DEVICES if arguments.all else [arguments.device]:
            verify_guest(device, arguments.timeout)


if __name__ == "__main__":
    main()
