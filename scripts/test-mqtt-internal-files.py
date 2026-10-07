#!/usr/bin/env python3
"""Test synthetic MQTT fixtures on loopback, inspect ext4, or boot QEMU.

Only contacts 127.0.0.1. The MQTT client uses no password or external broker.
File-origin probes edit only fixture files inside disposable QEMU snapshots.
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
import uuid

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / "meta-iotbench"
if not LAYER.is_dir():
    LAYER = Path("/opt/yocto/layers/meta-iotbench")
SOURCE = LAYER / "recipes-vulns/cwe862-mqtt-internal-files/files"
DEVICES = sorted(p.parent.name for p in (LAYER / "recipes-devices").glob("*/device-*.inc"))
SLUG = "cwe862-mqtt-internal-files"
DATA = "/usr/share/iotbench/mqtt-internal-files"
HELPER = "/usr/bin/iotbench-mqtt-internal-files"
SERVICE = "iotbench-mqtt-internal-files.service"
WARNING = ("INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — "
           "LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT")
TOPICS = {"device/config": "device.conf", "maintenance/info": "maintenance.dat"}
MQTT_DEVICES = set(DEVICES) - {"router", "ipcamera", "plc"}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def mqtt_string(value):
    encoded = value.encode()
    return struct.pack("!H", len(encoded)) + encoded


def variable_integer(value):
    encoded = bytearray()
    while True:
        digit = value % 128
        value //= 128
        encoded.append(digit | (128 if value else 0))
        if not value:
            return bytes(encoded)


def decode_integer(data, position):
    value = 0
    for count in range(4):
        require(position < len(data), "Truncated MQTT variable integer")
        digit = data[position]
        position += 1
        value += (digit & 127) << (7 * count)
        if not digit & 128:
            return value, position
    raise AssertionError("Invalid MQTT variable integer")


class Client:
    """Small MQTT 5 test client; clean session, no password, no remote host."""
    def __init__(self, port, username=None):
        self.socket = socket.create_connection(("127.0.0.1", port), timeout=5)
        try:
            self.socket.settimeout(10)
            flags = 2 | (128 if username is not None else 0)
            body = mqtt_string("MQTT") + bytes([5, flags]) + b"\x00\x1e\x00"
            body += mqtt_string("fixture-test-" + uuid.uuid4().hex)
            if username is not None:
                body += mqtt_string(username)
            self.send(0x10, body)
            kind, response = self.receive()
            require(kind == 0x20 and len(response) >= 3 and response[1] == 0,
                    f"Broker rejected MQTT 5 connection: {response!r}")
        except Exception:
            self.socket.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.socket.close()

    def send(self, kind, body):
        self.socket.sendall(bytes([kind]) + variable_integer(len(body)) + body)

    def exact(self, length):
        result = bytearray()
        while len(result) < length:
            chunk = self.socket.recv(length - len(result))
            require(chunk, "Broker closed connection")
            result.extend(chunk)
        return bytes(result)

    def receive(self):
        kind = self.exact(1)[0]
        encoded = bytearray()
        for _ in range(4):
            digit = self.exact(1)[0]
            encoded.append(digit)
            if not digit & 128:
                length, _ = decode_integer(encoded, 0)
                require(length <= 8192, "Unexpectedly large MQTT test packet")
                return kind, self.exact(length)
        raise AssertionError("Invalid MQTT remaining length")

    def subscribe(self, topic):
        self.send(0x82, b"\x00\x01\x00" + mqtt_string(topic) + b"\x00")
        kind, body = self.receive()
        require(kind == 0x90 and body[:2] == b"\x00\x01", "Missing SUBACK")
        length, position = decode_integer(body, 2)
        return body[position + length:]

    def publication(self):
        kind, body = self.receive()
        require(kind >> 4 == 3 and len(body) >= 2, "Expected MQTT publication")
        length = int.from_bytes(body[:2], "big")
        topic = body[2:2 + length].decode()
        position = 2 + length
        require(kind & 6 == 0, "Expected subscription QoS 0")
        properties, position = decode_integer(body, position)
        position += properties
        require(position <= len(body), "Truncated PUBLISH properties")
        return topic, body[position:], bool(kind & 1)

    def denied_publish(self, topic):
        # MQTT 5 supplies an explicit authorization failure reason in PUBACK.
        self.send(0x33, mqtt_string(topic) + b"\x00\x02\x00" + b"fixture-write-denied")
        kind, body = self.receive()
        require(kind == 0x40 and body[:2] == b"\x00\x02" and len(body) >= 3 and body[2] == 0x87,
                f"Public publish must return Not authorized (0x87): {topic}, {body!r}")


def fetch(topic, port, timeout=10):
    with Client(port) as client:
        require(client.subscribe(topic) == b"\x00", "Known topic subscription failed")
        client.socket.settimeout(timeout)
        received_topic, content, retained = client.publication()
        require(received_topic == topic, "Expected exact topic")
        return content


def wait_content(topic, expected, port, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if fetch(topic, port, timeout=1) == expected:
                return
        except (socket.timeout, ConnectionError):
            pass
        time.sleep(0.2)
    raise AssertionError(f"Topic did not contain expected current file bytes: {topic}")


def expected_file(filename, device):
    return (SOURCE / filename).read_bytes().replace(b"@DEVICE@", device.encode())


def verify_protocol(device, port):
    for topic, filename in TOPICS.items():
        require(fetch(topic, port) == expected_file(filename, device),
                f"Anonymous read differs from internal file: {topic}")
    print(f"PASS {device}: anonymous MQTT subscriptions expose both exact internal files", flush=True)
    with Client(port) as client:
        require(client.subscribe("#") == b"\x00", "Wildcard subscription failed")
        found = set()
        deadline = time.monotonic() + 10
        while found != set(TOPICS) and time.monotonic() < deadline:
            topic, content, _ = client.publication()
            if topic in TOPICS:
                require(content == expected_file(TOPICS[topic], device), "Wildcard data differs")
                found.add(topic)
        require(found == set(TOPICS), "Wildcard did not expose internal topics")
    for username in (None, "mqttfixture", "maintenance"):
        with Client(port, username=username) as client:
            for topic in (*TOPICS, "device/config/request", "file/read", "iotbench/test/state"):
                client.denied_publish(topic)
    # Unknown topic names and path-like names cannot select a filesystem file.
    for topic in ("file/read", "device/config/../../etc/passwd", "/etc/passwd", "device/config/request"):
        with Client(port) as client:
            result = client.subscribe(topic)
            require(result in (b"\x00", b"\x87"), "Unexpected unknown-topic SUBACK")
            client.socket.settimeout(0.5)
            try:
                client.publication()
            except socket.timeout:
                pass
            else:
                raise AssertionError("Unknown topic exposed a payload: " + topic)
    for topic, filename in TOPICS.items():
        require(fetch(topic, port) == expected_file(filename, device), "Denied writes changed retained content")
    print("PASS wildcard disclosure; public writes denied even with spoofed usernames; fixed topics only", flush=True)
    if device in MQTT_DEVICES:
        with Client(port) as client:
            require(client.subscribe(f"iotbench/{device}/#") == b"\x00", "Telemetry subscription failed")
            topic, content, _ = client.publication()
            require(topic.startswith(f"iotbench/{device}/") and content, "Native telemetry missing")
        print("PASS existing native MQTT telemetry uses the firmware-local publishing listener", flush=True)


def verify_image(path, debugfs):
    require(path.is_file(), f"Image not found: {path}")
    require(shutil.which(debugfs), f"debugfs not found: {debugfs}")
    with tempfile.TemporaryDirectory(prefix="iotbench-mqtt-inspect-") as temporary:
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
        require(metadata(DATA + "/internal") == (0o750, 0, 991), "Wrong internal directory permissions")
        for filename in TOPICS.values():
            name = DATA + "/internal/" + filename
            require(metadata(name) == (0o640, 0, 991), "Wrong internal file permissions")
            require(inspect("cat", name) == expected_file(filename, device), "Wrong synthetic file content")
        require(inspect("cat", DATA + "/publisher.c") == (SOURCE / "iotbench-mqtt-internal-files.c").read_bytes(),
                "Installed handler source differs from source used for analysis")
        truth = (SOURCE / "ground-truth.json").read_text().replace("@BINDIR@", "/usr/bin").replace("@DATADIR@", "/usr/share")
        require(json.loads(inspect("cat", DATA + "/ground-truth.json")) == json.loads(truth), "Wrong ground truth")
        require(WARNING.encode() in inspect("cat", "/etc/motd")
                and inspect("cat", DATA + "/NOTICE") == (SOURCE / "NOTICE").read_bytes(), "Warning missing")
        users = [line.split(":") for line in inspect("cat", "/etc/passwd").decode().splitlines()
                 if line.startswith("mqttfixture:")]
        require(len(users) == 1 and users[0][2:4] == ["991", "991"] and users[0][-1] == "/bin/false",
                "Wrong unprivileged daemon account")
        require(any(line.startswith("mqttfixture:!:") for line in inspect("cat", "/etc/shadow").decode().splitlines()),
                "Daemon account must have a locked password")
        # Modern Yocto uses /usr/lib/systemd/system through usrmerge.
        unit = "/usr/lib/systemd/system/" + SERVICE
        require(inspect("cat", unit) == (SOURCE / SERVICE).read_bytes().replace(b"@BINDIR@", b"/usr/bin"),
                "Wrong startup/service sandbox")
        for filename, installed in (
            ("mosquitto-iotbench.conf", "/etc/mosquitto/iotbench.conf"),
            ("iotbench-public.acl", "/etc/mosquitto/iotbench-public.acl"),
            ("iotbench-publish.acl", "/etc/mosquitto/iotbench-publish.acl"),
            ("mosquitto-iotbench.service.conf", "/usr/lib/systemd/system/mosquitto.service.d/10-iotbench-listener.conf"),
            ("iotbench-mqtt.service.conf", "/usr/lib/systemd/system/iotbench-mqtt.service.d/10-fixture-publisher.conf"),
        ):
            require(inspect("cat", installed) == (SOURCE / filename).read_bytes(), "Wrong MQTT config/ACL: " + installed)
        require(b"File not found" not in inspect("stat", "/etc/systemd/system/multi-user.target.wants/mosquitto.service"),
                "Broker is not enabled")
        require(b"File not found" not in inspect("stat", "/etc/systemd/system/multi-user.target.wants/" + SERVICE),
                "Service is not enabled")
        executable = Path(temporary) / "daemon.elf"
        inspect("dump", HELPER + " " + str(executable))
        elf = executable.read_bytes()
        require(elf.startswith(b"\x7fELF") and b"device/config" in elf and b"maintenance/info" in elf
                and DATA.encode() + b"/internal" in elf and b"mosquitto_publish" in elf, "ELF must contain the exact firmware mappings")
        print(f"PASS {device}: fixed internal files, MQTT ELF/mappings, unprivileged enabled service, warning and CWE-862 metadata", flush=True)
        print("PASS daemon SHA-256 " + hashlib.sha256(elf).hexdigest(), flush=True)


def verify_guest(device, timeout, port):
    firmware = f"{device}-{SLUG}"
    environment = dict(os.environ, FIRMWARE=firmware, QEMU_PERSIST="0", QEMU_MQTT_PORT=str(port))
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
              f"test \"$(stat -c '%u:%g:%a' {DATA}/internal/device.conf)\" = 0:991:640",
              "MQTT_STARTUP")
        verify_protocol(device, port)

        # Edits happen only inside this disposable guest, through its serial
        # console. No MQTT message selects a path or requests a file edit.
        target = DATA + "/internal/device.conf"
        backup = "/tmp/iotbench-mqtt-original.conf"
        guest(f"cp -p {target} {backup} && printf '%s\\n' 'MQTT_FILE_READ_PROBE=fixture-only' > {target}",
              "MQTT_REPLACE")
        wait_content("device/config", b"MQTT_FILE_READ_PROBE=fixture-only\n", port)
        guest(f"rm {target}", "MQTT_REMOVE")

        def require_cleared():
            # Wait for the bounded periodic publisher to remove the retained
            # value, then require a new subscription to receive no bytes.
            time.sleep(7)
            with Client(port) as client:
                require(client.subscribe("device/config") == b"\x00", "SUBACK missing")
                client.socket.settimeout(1)
                deadline = time.monotonic() + 1
                while time.monotonic() < deadline:
                    try:
                        _, content, _ = client.publication()
                    except socket.timeout:
                        return
                    require(not content, "Invalid fixed file left retained contents")

        require_cleared()
        guest(f"ln -s ../NOTICE {target}", "MQTT_SYMLINK")
        require_cleared()
        guest(f"rm {target} && printf '%1025s' 'fixture-only' > {target} && chown 0:991 {target} && chmod 0640 {target}",
              "MQTT_OVERSIZED")
        require_cleared()
        guest(f"rm {target} && mkfifo {target} && chown 0:991 {target} && chmod 0640 {target}", "MQTT_FIFO")
        require_cleared()
        guest(f"rm {target} && cp -p {backup} {target} && rm {backup}", "MQTT_RESTORE")
        wait_content("device/config", expected_file("device.conf", device), port)
        guest("systemctl restart mosquitto.service", "MQTT_BROKER_RESTART")
        wait_content("device/config", expected_file("device.conf", device), port)
        wait_content("maintenance/info", expected_file("maintenance.dat", device), port)
        guest(f"systemctl is-active --quiet {SERVICE} && "
              "grep -q '0100007F:075C .* 0A ' /proc/net/tcp",
              "MQTT_PRIVATE_LISTENER")
        print(f"PASS {firmware}: real file-to-MQTT flow, missing/symlink/size/FIFO rejection, restored bytes and broker restart; log {log_path}", flush=True)
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
    selection.add_argument("--get", choices=TOPICS, help="fetch one fixed topic anonymously")
    selection.add_argument("--device", choices=DEVICES, help="test an already running firmware")
    selection.add_argument("--boot", choices=DEVICES, help="boot and test one disposable firmware")
    selection.add_argument("--all", action="store_true", help="boot/test all devices sequentially")
    selection.add_argument("--image", type=Path, help="offline ext4/ext4.zst inspection")
    parser.add_argument("--port", type=int, default=int(os.environ.get("QEMU_MQTT_PORT", "1883")))
    parser.add_argument("--timeout", type=int, default=150, help="seconds per console step")
    parser.add_argument("--debugfs", default="debugfs", help="debugfs path for offline inspection")
    args = parser.parse_args()
    require(1 <= args.port <= 65535, "TCP port must be between 1 and 65535")
    if args.get:
        print(fetch(args.get, args.port).decode(), end="")
    elif args.image:
        verify_image(args.image, args.debugfs)
    elif args.device:
        verify_protocol(args.device, args.port)
    else:
        for device in DEVICES if args.all else [args.boot]:
            verify_guest(device, args.timeout, args.port)


if __name__ == "__main__":
    main()
