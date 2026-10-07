#!/usr/bin/env python3
"""Read/test synthetic CoAP fixtures on loopback, inspect ext4, or boot QEMU.

This client only contacts 127.0.0.1 at the chosen UDP port. It performs no host
discovery and sends no command or client-selected filesystem path to the daemon.
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
import socket
import struct
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / "meta-iotbench"
if not LAYER.is_dir():
    LAYER = Path("/opt/yocto/layers/meta-iotbench")
SOURCE = LAYER / "recipes-vulns/cwe862-coap-internal-files/files"
DEVICES = sorted(p.parent.name for p in (LAYER / "recipes-devices").glob("*/device-*.inc"))
SLUG = "cwe862-coap-internal-files"
DATA = "/usr/share/iotbench/coap-internal-files"
HELPER = "/usr/bin/iotbench-coap-internal-files"
SERVICE = "iotbench-coap-internal-files.service"
WARNING = ("INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — "
           "LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT")
RESOURCES = {"/device/config": "device.conf", "/maintenance/info": "maintenance.dat"}
request_id = 0


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def option_number(value):
    if value < 13:
        return value, b""
    if value < 269:
        return 13, bytes([value - 13])
    require(value < 65805, "CoAP option too large")
    return 14, struct.pack("!H", value - 269)


def encode_option(delta, value):
    number, number_extra = option_number(delta)
    length, length_extra = option_number(len(value))
    return bytes([(number << 4) | length]) + number_extra + length_extra + value


def packet(path, method=1, query=None, payload=b"", confirmable=True):
    global request_id
    request_id = request_id % 65535 + 1
    token = struct.pack("!H", request_id)
    result = bytes([0x42 if confirmable else 0x52, method]) + token + token
    previous = 0
    for segment in path.lstrip("/").split("/"):
        if segment:
            result += encode_option(11 - previous, segment.encode())
            previous = 11
    if query is not None:
        result += encode_option(15 - previous, query.encode())
    if payload:
        result += b"\xff" + payload
    return result


def decode_response(response, request):
    require(len(response) >= 6 and response[0] >> 6 == 1, "Invalid CoAP response")
    require(response[0] & 15 == 2 and response[4:6] == request[4:6], "Wrong response token")
    require(response[0] >> 4 & 3 == (2 if request[0] == 0x42 else 1), "Wrong CoAP response type")
    if request[0] == 0x42:
        require(response[2:4] == request[2:4], "Wrong ACK message ID")
    position = 6
    number = 0
    options = {}

    def extended(nibble):
        nonlocal position
        require(nibble != 15, "Reserved CoAP option nibble")
        count = 1 if nibble == 13 else 2 if nibble == 14 else 0
        if not count:
            return nibble
        require(position + count <= len(response), "Truncated CoAP option")
        value = int.from_bytes(response[position:position + count], "big")
        position += count
        return value + (13 if count == 1 else 269)

    while position < len(response) and response[position] != 255:
        header = response[position]
        position += 1
        number += extended(header >> 4)
        length = extended(header & 15)
        require(position + length <= len(response), "Truncated option value")
        options[number] = response[position:position + length]
        position += length
    content = response[position + 1:] if position < len(response) else b""
    if response[1] == 69:
        require(12 in options and int.from_bytes(options[12], "big") == 0,
                "Expected text/plain Content-Format 0")
    return response[1], content


def exchange(request, port, duplicate=False):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
        client.connect(("127.0.0.1", port))
        client.settimeout(2)
        received = None
        for _ in range(3):
            client.send(request)
            try:
                received = client.recv(4096)
                break
            except socket.timeout:
                continue
        require(received is not None, f"No CoAP response on loopback UDP {port}")
        result = decode_response(received, request)
        if duplicate:
            client.send(request)
            repeated = decode_response(client.recv(4096), request)
            require(repeated == result, "Repeated GET changed the response")
        return result


def expected_file(filename, device):
    return (SOURCE / filename).read_bytes().replace(b"@DEVICE@", device.encode())


def verify_protocol(device, port):
    for uri, filename in RESOURCES.items():
        for confirmable in (True, False):
            code, content = exchange(packet(uri, confirmable=confirmable), port, duplicate=confirmable)
            require(code == 69 and content == expected_file(filename, device),
                    f"{uri}: expected 2.05 Content with exact internal fixture bytes, got {code}")
    print(f"PASS {device}: unauthenticated CON/NON CoAP GET exposes both exact internal files", flush=True)
    for uri in ("/missing", "/device/config/../maintenance/info", "/device/%2e%2e/config", "/etc/passwd"):
        code, content = exchange(packet(uri), port)
        require(code == 132, f"Unknown URI must return 4.04: {uri}, got {code}")
        require(b"COAP_INTERNAL_" not in content, "Unknown URI leaked internal content")
    for method in (2, 3, 4):
        code, content = exchange(packet("/device/config", method=method, payload=b"fixture-write-test"), port)
        require(code == 133, f"Write method must return 4.05, got {code}")
        require(b"COAP_INTERNAL_" not in content, "Write request leaked internal content")
    for uri in RESOURCES:
        for request in (packet(uri, query="path=fixture-only"), packet(uri, payload=b"fixture-only")):
            code, content = exchange(request, port)
            require(code == 128 and b"COAP_INTERNAL_" not in content, "Query/body must return 4.00")
        code, content = exchange(packet(uri), port)
        require(code == 69 and content == expected_file(RESOURCES[uri], device), "GET controls modified data")
    print("PASS fixed resources only; unknown URIs, queries, bodies and write methods rejected", flush=True)


def verify_image(path, debugfs):
    require(path.is_file(), f"Image not found: {path}")
    require(shutil.which(debugfs), f"debugfs not found: {debugfs}")
    with tempfile.TemporaryDirectory(prefix="iotbench-coap-inspect-") as temporary:
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
            mode = re.search(r"Mode:\s+([0-7]+)", info)
            owner = re.search(r"User:\s+(\d+)\s+Group:\s+(\d+)", info)
            require(mode and owner, f"Cannot parse inode metadata: {name}")
            return int(mode[1], 8), int(owner[1]), int(owner[2])

        identity = inspect("cat", "/etc/iotbench/device.conf").decode()
        match = re.search(r'^DEVICE_CLASS="([a-z]+)"$', identity, re.M)
        require(match and match[1] in DEVICES, "Unsupported device identity")
        device = match[1]
        require(metadata(HELPER) == (0o755, 0, 0), "Daemon must be ordinary root-owned 0755")
        require(metadata(DATA + "/internal") == (0o750, 0, 992), "Wrong internal directory permissions")
        for filename in RESOURCES.values():
            name = DATA + "/internal/" + filename
            require(metadata(name) == (0o640, 0, 992), "Wrong internal file permissions")
            require(inspect("cat", name) == expected_file(filename, device), "Wrong synthetic file content")
        require(inspect("cat", DATA + "/handler.c") == (SOURCE / "iotbench-coap-internal-files.c").read_bytes(),
                "Installed handler source differs from source used for analysis")
        truth = (SOURCE / "ground-truth.json").read_text().replace("@BINDIR@", "/usr/bin").replace("@DATADIR@", "/usr/share")
        require(json.loads(inspect("cat", DATA + "/ground-truth.json")) == json.loads(truth), "Wrong ground truth")
        require(WARNING.encode() in inspect("cat", "/etc/motd")
                and inspect("cat", DATA + "/NOTICE") == (SOURCE / "NOTICE").read_bytes(), "Warning missing")
        users = [line.split(":") for line in inspect("cat", "/etc/passwd").decode().splitlines()
                 if line.startswith("coapfixture:")]
        require(len(users) == 1 and users[0][2:4] == ["992", "992"] and users[0][-1] == "/bin/false",
                "Wrong unprivileged daemon account")
        require(any(line.startswith("coapfixture:!:") for line in inspect("cat", "/etc/shadow").decode().splitlines()),
                "Daemon account must have a locked password")
        # Modern Yocto uses /usr/lib/systemd/system through usrmerge.
        unit = "/usr/lib/systemd/system/" + SERVICE
        require(inspect("cat", unit) == (SOURCE / SERVICE).read_bytes().replace(b"@BINDIR@", b"/usr/bin"),
                "Wrong startup/service sandbox")
        require(b"File not found" not in inspect("stat", "/etc/systemd/system/multi-user.target.wants/" + SERVICE),
                "Service is not enabled")
        executable = Path(temporary) / "daemon.elf"
        inspect("dump", HELPER + " " + str(executable))
        elf = executable.read_bytes()
        require(elf.startswith(b"\x7fELF") and b"device/config" in elf and b"maintenance/info" in elf
                and DATA.encode() + b"/internal" in elf, "ELF must contain the exact firmware mappings")
        print(f"PASS {device}: fixed internal files, CoAP ELF/mappings, unprivileged enabled service, warning and CWE-862 metadata", flush=True)
        print("PASS daemon SHA-256 " + hashlib.sha256(elf).hexdigest(), flush=True)


def verify_guest(device, timeout, port):
    firmware = f"{device}-{SLUG}"
    environment = dict(os.environ, FIRMWARE=firmware, QEMU_PERSIST="0", QEMU_COAP_PORT=str(port))
    master, slave = pty.openpty()
    transcript = bytearray()
    process = None
    log_path = ROOT / "deploy-images" / firmware / environment.get("YOCTO_MACHINE", "qemuarm64") / "validation-console.log"
    try:
        process = subprocess.Popen([str(ROOT / "scripts/run-qemu.sh")], cwd=ROOT, env=environment,
                                   stdin=slave, stdout=slave, stderr=slave)
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

        def guest(command, marker):
            os.write(master, (command + f"; printf '\\n{marker}=%s\\n' \"$?\"\n").encode())
            wait_for(b"\r\n" + marker.encode() + b"=")
            wait_for(b"\r\n")
            require(re.search(rb"(?m)^" + marker.encode() + rb"=0$", transcript.replace(b"\r", b"")),
                    f"Guest operation failed: {marker}")

        wait_for(b"login:")
        os.write(master, b"root\n")
        wait_for(b"Password:")
        os.write(master, b"routeradmin\n")
        wait_for(b"root@")
        require(WARNING.encode() in transcript, "Required login warning missing")
        guest(f"systemctl is-active --quiet {SERVICE} && "
              f"grep -Fx 'DEVICE_CLASS=\"{device}\"' /etc/iotbench/device.conf && "
              f"test \"$(stat -c '%u:%g:%a' {DATA}/internal/device.conf)\" = 0:992:640",
              "COAP_STARTUP")
        verify_protocol(device, port)

        # Only the synthetic fixed file is changed inside this disposable guest.
        # Observe the changed bytes over CoAP to prove the real read-to-response
        # relationship, then test missing/symlink/oversized data failures.
        target = DATA + "/internal/device.conf"
        backup = "/tmp/iotbench-coap-original.conf"
        guest(f"cp -p {target} {backup} && printf '%s\\n' 'COAP_FILE_READ_PROBE=fixture-only' > {target}",
              "COAP_REPLACE")
        require(exchange(packet("/device/config"), port) == (69, b"COAP_FILE_READ_PROBE=fixture-only\n"),
                "Response did not originate from the current internal file")
        guest(f"rm {target}", "COAP_REMOVE")
        require(exchange(packet("/device/config"), port)[0] == 160, "Missing file must fail with 5.00")
        guest(f"ln -s ../NOTICE {target}", "COAP_SYMLINK")
        require(exchange(packet("/device/config"), port)[0] == 160, "Symlink must fail with 5.00")
        guest(f"rm {target} && printf '%513s' 'fixture-only' > {target} && chown 0:992 {target} && chmod 0640 {target}",
              "COAP_OVERSIZED")
        require(exchange(packet("/device/config"), port)[0] == 160, "Oversized file must fail with 5.00")
        guest(f"cp -p {backup} {target} && rm {backup}", "COAP_RESTORE")
        require(exchange(packet("/device/config"), port) == (69, expected_file("device.conf", device)),
                "Original fixture data was not restored")
        print(f"PASS {firmware}: real file-to-CoAP data flow, missing/symlink/size rejection and restored bytes; log {log_path}", flush=True)
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
    selection.add_argument("--get", choices=RESOURCES, help="manually fetch one predefined resource")
    selection.add_argument("--device", choices=DEVICES, help="test an already running firmware")
    selection.add_argument("--boot", choices=DEVICES, help="boot and test one disposable firmware")
    selection.add_argument("--all", action="store_true", help="boot/test all devices sequentially")
    selection.add_argument("--image", type=Path, help="offline ext4/ext4.zst inspection")
    parser.add_argument("--port", type=int, default=int(os.environ.get("QEMU_COAP_PORT", "5683")))
    parser.add_argument("--timeout", type=int, default=150, help="seconds per console step")
    parser.add_argument("--debugfs", default="debugfs", help="debugfs path for offline inspection")
    args = parser.parse_args()
    require(1 <= args.port <= 65535, "UDP port must be between 1 and 65535")
    if args.get:
        code, content = exchange(packet(args.get), args.port)
        print(f"CoAP {code >> 5}.{code & 31:02d}")
        print(content.decode(), end="")
        require(code == 69, "Expected 2.05 Content")
    elif args.image:
        verify_image(args.image, args.debugfs)
    elif args.device:
        verify_protocol(args.device, args.port)
    else:
        for device in DEVICES if args.all else [args.boot]:
            verify_guest(device, args.timeout, args.port)


if __name__ == "__main__":
    main()
