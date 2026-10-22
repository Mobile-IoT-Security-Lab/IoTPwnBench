#!/usr/bin/env python3
"""Build/test the isolated CWE-120 fixture locally, or verify disposable QEMU images.

The local mode explicitly enables synthetic fixture configuration. It uses only
Unix sockets; oversized input is sent exclusively to ASan-instrumented binaries.
"""
import argparse
import json
import os
from pathlib import Path
import pty
import re
import select
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / "meta-iotbench"
if not LAYER.is_dir():
    LAYER = Path("/opt/yocto/layers/meta-iotbench")
DEVICES = sorted(p.parent.name for p in (LAYER / "recipes-devices").glob("*/device-*.inc"))
SLUG = "cwe120-service-buffer-overflow"
SOURCE = LAYER / "recipes-vulns" / SLUG / "files"
DATA = "/usr/share/iotbench/service-buffer-overflow"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def verify_integration():
    truth = json.loads((SOURCE / "ground-truth.json").read_text())
    lines = (SOURCE / "fixture-label-service.c").read_text().splitlines()
    for key, expression in (
        ("copy_line", "label[i] = field[i];"),
        ("buffer_line", "volatile char label[32];"),
        ("handler_call_line", "if (!handle_label_request(field, length))"),
        ("receive_line", "if (receive_exact(fd, (unsigned char *)field, length) != 0)"),
    ):
        require(lines[truth[key] - 1].strip() == expression, f"Stale source location: {key}")
    require(truth["cwe"] == "CWE-120" and truth["capacity"] == 32,
            "Incorrect ground truth")
    recipes = LAYER / "recipes-images"
    require(DEVICES and DEVICES == sorted(p.name.removeprefix("iotbench-").removesuffix(
        f"-{SLUG}.bb") for p in recipes.glob(f"iotbench-*-{SLUG}.bb")),
        "Image recipes must cover every supported device exactly once")
    for device in DEVICES:
        recipe = (recipes / f"iotbench-{device}-{SLUG}.bb").read_text()
        for expected in ("require recipes-images/iotbench-image.inc",
                         f"require recipes-devices/{device}/device-{device}.inc",
                         "require recipes-images/iotbench-service-buffer-overflow.inc",
                         f'IOTBENCH_VULN_INSTALL = "{SLUG}"', 'IOTBENCH_CWE = "CWE-120"'):
            require(expected in recipe, f"Incorrect integration for {device}: {expected}")
    print(f"PASS exact source locations, ground truth and all {len(DEVICES)} device recipes", flush=True)


def verify_local(cc):
    require(os.geteuid() != 0, "Run local fixture validation as an unprivileged user")
    source = SOURCE / "fixture-label-service.c"
    # A short private path also fits macOS sockaddr_un.sun_path (104 bytes).
    with tempfile.TemporaryDirectory(prefix="cwe120-", dir="/tmp") as temporary:
        temporary = Path(temporary)
        binary, diagnostic = temporary / "native", temporary / "asan"
        flags = ["-std=c99", "-O2", "-g", "-fno-inline", "-Wall", "-Wextra", "-Werror",
                 "-D_FORTIFY_SOURCE=2", "-fstack-protector-strong", "-fPIE"]
        if sys.platform.startswith("linux"):
            flags += ["-pie", "-Wl,-z,relro,-z,now"]
        denied = subprocess.run([cc, *flags, str(source), "-o", str(binary)],
                                capture_output=True, text=True, timeout=60)
        require(denied.returncode != 0 and "requires an explicit synthetic fixture build" in denied.stderr,
                "Source compiled without the fixture build opt-in")
        print("PASS compiler refuses ordinary builds without the fixture definition", flush=True)
        flags += ["-DIOTBENCH_CWE120_FIXTURE=1"]

        def build(path, output, sanitize=False):
            instrumentation = ["-fsanitize=address", "-fno-omit-frame-pointer"] if sanitize else []
            if sanitize and sys.platform == "darwin":
                # Apple ASan predefines Fortify to 0. Keep our explicit level 2;
                # suppress only the resulting macro-redefinition warning.
                instrumentation += ["-Wno-macro-redefined"]
            subprocess.run([cc, *flags, *instrumentation, str(path), "-o", str(output)],
                           check=True, timeout=60)

        build(source, binary)
        build(source, diagnostic, True)
        environment = dict(os.environ, TMPDIR=str(temporary), PYTHONDONTWRITEBYTECODE="1")
        test = [sys.executable, str(SOURCE / "test-service.py"), "--fixture-test",
                "--binary", str(binary), "--asan", str(diagnostic)]
        subprocess.run(test, env=environment, check=True, timeout=60)
        # Correct only a disposable control to prove the diagnostic depends on
        # the missing destination-capacity check. Firmware source stays vulnerable.
        control = temporary / "safe-control.c"
        original = source.read_text()
        needle = "    volatile char label[32];"
        require(original.count(needle) == 1, "Cannot construct negative control")
        control.write_text(original.replace(needle, needle +
                           "\n    if (length >= sizeof(label))\n        return 0;", 1))
        build(control, diagnostic, True)
        subprocess.run([*test, "--safe-control"], env=environment, check=True, timeout=60)
    print("PASS optimized native and ASan builds retain Fortify and stack protection", flush=True)


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
                require(process.poll() is None, f"QEMU exited: {process.returncode}")
                ready, _, _ = select.select([master], [], [], 1)
                if ready:
                    transcript.extend(os.read(master, 65536))
            raise TimeoutError(f"Timed out waiting for {token!r}")

        wait_for(b"login:")
        os.write(master, b"root\n")
        wait_for(b"Password:")
        os.write(master, b"routeradmin\n")
        wait_for(b"root@")
        command = (f"sh {DATA}/test-guest.sh {device}; "
                   "printf '\\nSERVICE_BUFFER_CHECK_EXIT=%s\\n' \"$?\"\n")
        os.write(master, command.encode())
        wait_for(b"\r\nSERVICE_BUFFER_CHECK_EXIT=")
        wait_for(b"\r\n")
        output = transcript.replace(b"\r", b"")
        require(re.search(rb"(?m)^SERVICE_BUFFER_CHECK_EXIT=0$", output), "Guest regression failed")
        for evidence in (b"PASS registered systemd service endpoint", b"PASS service refuses",
                         b"PASS normal service requests", b"PASS strict framing",
                         b"PASS socket input causes ASan-confirmed"):
            require(evidence in output, f"Missing guest evidence: {evidence!r}")
        print(f"PASS {firmware}: disabled service, explicit start, normal/boundary/malformed "
              f"requests and ASan copy violation; networking disabled; log {log_path}", flush=True)
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
    selection.add_argument("--local", action="store_true", help="explicit isolated host test build with ASan")
    selection.add_argument("--device", choices=DEVICES, help="boot and verify one device fixture")
    selection.add_argument("--all", action="store_true", help="boot all device fixtures sequentially")
    parser.add_argument("--cc", default="cc", help="host C compiler with AddressSanitizer support")
    parser.add_argument("--timeout", type=int, default=150, help="seconds per QEMU console step")
    arguments = parser.parse_args()
    verify_integration()
    if arguments.local:
        verify_local(arguments.cc)
    else:
        for device in DEVICES if arguments.all else [arguments.device]:
            verify_guest(device, arguments.timeout)


if __name__ == "__main__":
    main()
