#!/usr/bin/env python3
"""Local socket regression; oversized requests run only against the ASan build."""
import argparse
import os
from pathlib import Path
import resource
import socket
import struct
import subprocess
import tempfile
import time

RESPONSE = b"SYNTHETIC_LABEL_UPDATED\n"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def limits():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))


def request(endpoint, wire, fragment=False):
    deadline = time.monotonic() + 5
    while True:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(5)
        try:
            client.connect(str(endpoint))
            break
        except (FileNotFoundError, ConnectionRefusedError):
            # bind makes the path visible just before listen accepts connections.
            client.close()
            require(time.monotonic() < deadline, "Service connection timeout")
            time.sleep(0.01)
        except BaseException:
            client.close()
            raise
    with client:
        require(client.recv(1) == b"\x01", "Missing service readiness byte")
        if fragment:
            for byte in wire:
                client.sendall(bytes([byte]))
        else:
            client.sendall(wire)
        client.shutdown(socket.SHUT_WR)
        response = bytearray()
        try:
            while True:
                chunk = client.recv(4096)
                if not chunk:
                    break
                response.extend(chunk)
                require(len(response) <= 4096, "Unbounded response")
        except ConnectionResetError:
            pass  # Malformed frames may leave unread data; ASan may close abruptly.
        return bytes(response)


def frame(field):
    return struct.pack("!H", len(field)) + field


def run_case(binary, wire, expected_status=0, diagnostic=False, fragment=False):
    with tempfile.TemporaryDirectory(prefix="label-") as temporary:
        endpoint = Path(temporary) / "service.sock"
        environment = dict(os.environ, IOTBENCH_CWE120_FIXTURE="1",
                           ASAN_OPTIONS="detect_leaks=0:abort_on_error=0:halt_on_error=1:symbolize=1:disable_coredump=1")
        with tempfile.TemporaryFile() as errors:
            process = subprocess.Popen([str(binary), "--fixture-test", "--socket", str(endpoint)],
                                       stdout=subprocess.DEVNULL, stderr=errors,
                                       env=environment, preexec_fn=limits)
            try:
                deadline = time.monotonic() + 5
                while not endpoint.exists():
                    require(process.poll() is None, "Service exited before creating socket")
                    require(time.monotonic() < deadline, "Socket startup timeout")
                    time.sleep(0.01)
                require(endpoint.stat().st_mode & 0o777 == 0o700, "Socket is not owner-only")
                response = request(endpoint, wire, fragment)
                status = process.wait(timeout=8)
                errors.seek(0)
                stderr = errors.read().decode(errors="replace")
                if diagnostic:
                    require(status != 0 and "AddressSanitizer: stack-buffer-overflow" in stderr
                            and "WRITE of size 1 " in stderr and "handle_label_request" in stderr
                            and "label" in stderr,
                            f"Missing copy-specific ASan evidence: {status}\n{stderr}")
                    require(not response, "Oversized diagnostic request returned success")
                    print(stderr, end="", flush=True)
                else:
                    require(status == expected_status,
                            f"Unexpected exit {status} from {binary.name}, frame={wire!r}: {stderr}")
                    require(response == (RESPONSE if status == 0 else b""), "Incorrect response")
                    require("AddressSanitizer" not in stderr, f"Unexpected ASan diagnostic: {stderr}")
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)


def regression(binary, diagnostic, safe_control=False):
    require(os.geteuid() != 0, "Run socket tests as an unprivileged user")
    for candidate in (binary, diagnostic):
        for arguments, enabled in (([], "1"), (["--fixture-test"], "0")):
            denied = subprocess.run([str(candidate), *arguments],
                                    env=dict(os.environ, IOTBENCH_CWE120_FIXTURE=enabled),
                                    capture_output=True, timeout=5, preexec_fn=limits)
            require(denied.returncode == 2 and not denied.stdout
                    and b"AddressSanitizer" not in denied.stderr, "Startup opt-in was bypassed")
    print("PASS service refuses missing runtime flag or fixture configuration", flush=True)
    for candidate in (binary, diagnostic):
        for field in (b"SYNTHETIC_DEVICE_NAME", b"S", b"S" * 31):
            run_case(candidate, frame(field), fragment=True)
    print("PASS normal service requests and 31-byte boundary on native and ASan builds", flush=True)
    malformed = [b"", b"\x00", b"\x00\x00", b"\x04\x01", b"\x00\x04SYN",
                 frame(b"SYN") + b"X", frame(b"SYN\x00THETIC"), frame(b"SYN\nTHETIC"), frame(b"\xff")]
    for wire in malformed:
        run_case(diagnostic, wire, expected_status=2)
    print("PASS strict framing, termination, ASCII and protocol size rejection", flush=True)
    for field in (b"S" * 32, b"SYNTHETIC_SERVICE_REQUEST_" * 4, b"S" * 1024):
        run_case(diagnostic, frame(field), expected_status=2, diagnostic=not safe_control)
    if safe_control:
        print("PASS corrected temporary control rejects all oversized labels without ASan errors", flush=True)
    else:
        print("PASS socket input causes ASan-confirmed unchecked copy stack-buffer-overflow (CWE-120/CWE-121)", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-test", required=True, action="store_true",
                        help="explicitly opt into this isolated synthetic fixture test")
    parser.add_argument("--safe-control", action="store_true", help="expect a corrected temporary test build")
    parser.add_argument("--binary", type=Path, default=Path("/usr/bin/fixture-label-service"))
    parser.add_argument("--asan", type=Path, default=Path("/usr/share/iotbench/service-buffer-overflow/fixture-label-service-asan"))
    parser.add_argument("--request", type=Path, help="send one normal request to an already running service")
    arguments = parser.parse_args()
    if arguments.request:
        require(request(arguments.request, frame(b"SYNTHETIC_DEVICE_NAME")) == RESPONSE, "Service response mismatch")
        print("PASS registered systemd service endpoint reaches the native handler", flush=True)
    else:
        regression(arguments.binary, arguments.asan, arguments.safe_control)
