#!/usr/bin/env python3
"""Explicit local synthetic sessions; optional real Linux loopback packet capture."""

import argparse
import errno
import json
import os
from pathlib import Path
import select
import socket
import stat
import struct
import subprocess
import sys
import threading
import time

USER = b'telnet-fixture'
PASSWORD = b'Fixture-Telnet-Only-42'


def check(condition, message):
    if not condition:
        raise AssertionError(message)


class Capture:
    """Save actual kernel frames, never synthesize packets from a transcript."""

    def __init__(self, required):
        self.frames = []
        self.ports = set()
        self.stopped = threading.Event()
        self.socket = None
        self.thread = None
        self.failure = None
        try:
            self.socket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0800))
            self.socket.bind(('lo', 0))
            self.socket.settimeout(0.05)
        except (AttributeError, OSError) as error:
            if self.socket is not None:
                self.socket.close()
            self.socket = None
            if required:
                raise RuntimeError('Real packet capture requires Linux CAP_NET_RAW: ' + str(error))
            print('SKIP real packet capture: ' + str(error), flush=True)

    @staticmethod
    def packet(frame):
        if len(frame) < 54 or frame[12:14] != b'\x08\x00' or frame[23] != 6:
            return None
        if frame[26:30] != b'\x7f\x00\x00\x01' or frame[30:34] != b'\x7f\x00\x00\x01':
            return None
        ip_size = (frame[14] & 15) * 4
        offset = 14 + ip_size
        if ip_size < 20 or len(frame) < offset + 20:
            return None
        source, destination = struct.unpack('!HH', frame[offset:offset + 4])
        tcp_size = (frame[offset + 12] >> 4) * 4
        ip_total = struct.unpack('!H', frame[16:18])[0]
        if tcp_size < 20 or ip_total < ip_size + tcp_size:
            return None
        return source, destination, frame[offset + tcp_size:14 + ip_total]

    def start(self):
        if self.socket is None:
            return

        def collect():
            try:
                while not self.stopped.is_set():
                    try:
                        frame = self.socket.recv(65535)
                    except socket.timeout:
                        continue
                    packet = self.packet(frame)
                    if packet and (packet[0] in self.ports or packet[1] in self.ports):
                        self.frames.append((time.time(), frame))
            except OSError as error:
                self.failure = error

        self.thread = threading.Thread(target=collect, daemon=True)
        self.thread.start()

    def finish(self, path):
        if self.socket is None:
            return
        # Drain frames already queued at the end of the final client exchange.
        time.sleep(0.1)
        self.stopped.set()
        self.thread.join(timeout=2)
        self.socket.close()
        check(not self.thread.is_alive() and self.failure is None, 'Packet collector failed')
        if path:
            with Path(path).open('wb') as output:
                output.write(struct.pack('<IHHIIII', 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1))
                for timestamp, frame in self.frames:
                    seconds = int(timestamp)
                    output.write(struct.pack('<IIII', seconds, int((timestamp - seconds) * 1000000),
                                             len(frame), len(frame)))
                    output.write(frame)

    def verify(self):
        if self.socket is None:
            return
        payload = b''.join(self.packet(frame)[2] for _, frame in self.frames)
        for token in (USER, PASSWORD, b'STATUS', b'SYNTHETIC STATUS: nominal'):
            check(token in payload, 'Missing plaintext in actual captured TCP payload: ' + repr(token))
        print('PASS actual loopback packet payloads contain credentials and session data', flush=True)


def external_addresses():
    """Inspect only addresses already assigned locally; no DNS or external probes."""
    import fcntl
    addresses = []
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as control:
        for _, name in socket.if_nameindex():
            try:
                result = fcntl.ioctl(control, 0x8915, struct.pack('256s', name.encode()[:15]))
            except OSError:
                continue
            address = socket.inet_ntoa(result[20:24])
            if not address.startswith('127.'):
                addresses.append(address)
    return sorted(set(addresses))


def run_tests(root, pcap=None, require_pcap=False, transcript_path=None):
    root = Path(root)
    executable = root / 'usr/bin/fixture-telnet'
    data = root / 'usr/share/iotbench/unencrypted-traffic'
    auth = root / 'etc/iotbench/telnet-auth.json'
    manifest = data / 'build-config.json'
    original_auth, original_build = auth.read_bytes(), manifest.read_bytes()
    auth_mode, build_mode = stat.S_IMODE(auth.stat().st_mode), stat.S_IMODE(manifest.stat().st_mode)
    check(auth_mode == 0o666, 'CWE-276 service policy must be installed mode 0666')
    check(json.loads(original_auth)['authentication'] == 'password-only', 'Missing weak policy')
    build = json.loads(original_build)
    check(build['mode'] == 'fixture' and build['enabled'] is True, 'Not an opted-in fixture')
    print('PASS installed hard-coded test credentials, password-only policy and mode 0666', flush=True)
    records = []
    capture = Capture(require_pcap)
    capture.start()
    external = external_addresses()
    isolation_checks = [0]

    def drop_privileges():
        if os.geteuid() == 0:
            # Capture remains in the parent; the service never needs root.
            import pwd
            nobody = pwd.getpwnam('nobody')
            mappings = [tuple(map(int, line.split()))
                        for line in Path('/proc/self/uid_map').read_text().splitlines()]
            if not any(start <= nobody.pw_uid < start + count for start, _, count in mappings):
                # A single-user rootless user namespace already maps this process
                # to the unprivileged caller; nobody is not representable there.
                return
            os.setgroups([])
            os.setgid(nobody.pw_gid)
            os.setuid(nobody.pw_uid)

    def process(arguments):
        return subprocess.Popen([sys.executable, str(executable)] + arguments,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                preexec_fn=drop_privileges if os.geteuid() == 0 else None)

    def refused(arguments):
        child = process(arguments)
        try:
            stdout, stderr = child.communicate(timeout=5)
            check(child.returncode == 2 and not stdout and stderr,
                  'Service accepted forbidden startup: ' + repr(arguments))
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()

    def exchange(username=USER, password=PASSWORD, accept=True, commands=True, negotiate=False,
                 malformed=None, newline=b'\r\n'):
        child = process(['--fixture-test', '--port', '0'])
        try:
            ready, _, _ = select.select([child.stdout], [], [], 5)
            check(ready, 'Service did not become ready')
            line = child.stdout.readline()
            if not line:
                raise AssertionError('Service failed: ' + child.stderr.read().decode(errors='replace'))
            endpoint = json.loads(line)
            check(endpoint['host'] == '127.0.0.1', 'Non-loopback listener')
            port = endpoint['port']
            capture.ports.add(port)
            # No connection is made to an address outside this machine.
            for address in ['127.0.0.2'] + external:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                    probe.settimeout(1)
                    result = probe.connect_ex((address, port))
                    check(result == errno.ECONNREFUSED,
                          'Expected local interface refusal, got {} on {}'.format(result, address))
                    if address in external:
                        isolation_checks[0] += 1
            with socket.create_connection(('127.0.0.1', port), timeout=3) as connection:
                def send(value):
                    connection.sendall(value)
                    records.append({'direction': 'client-to-service', 'hex': value.hex()})

                def until(token):
                    value = bytearray()
                    while not value.endswith(token):
                        part = connection.recv(1)
                        check(part, 'Premature EOF waiting for ' + repr(token))
                        value.extend(part)
                        check(len(value) < 4096, 'Oversized response')
                    records.append({'direction': 'service-to-client', 'hex': bytes(value).hex()})
                    return bytes(value)

                until(b'login: ')
                if malformed is not None:
                    send(malformed)
                    try:
                        check(connection.recv(1) == b'', 'Malformed input accepted')
                    except ConnectionResetError:
                        pass
                else:
                    if negotiate:
                        # WILL ECHO / DO SUPPRESS-GO-AHEAD, split across TCP writes.
                        for value in (b'\xff', b'\xfb', b'\x01', b'\xff\xfd\x03', b'\xff\xfd\x2e'):
                            send(value)
                        send(b'\xff\xfa\x18\x00synthetic-terminal\xff\xf0')
                    send(username + newline)
                    reply = until(b'Password: ')
                    if negotiate:
                        check(b'\xff\xfe\x01' in reply and b'\xff\xfc\x03' in reply
                              and b'\xff\xfc\x2e' in reply,
                              'Telnet options were not refused')
                    send(password + newline)
                    if not accept:
                        check(until(b'\r\n') == b'Authentication failed\r\n',
                              'Incorrect password/identity accepted')
                    else:
                        check(b'Synthetic authentication accepted' in until(b'fixture> '),
                              'Synthetic login failed')
                        if commands:
                            for command, expected in (
                                (b'STATUS', b'SYNTHETIC STATUS: nominal\r\nfixture> '),
                                (b'HELP', b'STATUS HELP QUIT (predefined responses only)\r\nfixture> '),
                                (b'id', b'Unknown synthetic command\r\nfixture> '),
                                (b'/bin/sh', b'Unknown synthetic command\r\nfixture> '),
                            ):
                                send(command + newline)
                                check(until(b'fixture> ') == expected, 'Non-synthetic command response')
                        send(b'QUIT' + newline)
                        check(until(b'\r\n') == b'Goodbye fixture\r\n', 'Missing close response')
            child.communicate(timeout=5)
            check(child.returncode == 0, 'Fixture process failed')
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()
            child.stdout.close()
            child.stderr.close()

    try:
        refused([])
        refused(['--fixture-test', '--host', '0.0.0.0'])
        for invalid in ({'mode': 'production', 'enabled': True, 'machine': 'qemuarm64'},
                        {'mode': 'fixture', 'enabled': False, 'machine': 'qemuarm64'},
                        {'mode': 'fixture', 'enabled': True, 'machine': 'real-device'}):
            manifest.write_text(json.dumps(invalid))
            refused(['--fixture-test'])
        manifest.write_bytes(original_build)
        exchange(negotiate=True)
        exchange(newline=b'\r\x00', commands=False)
        exchange(password=b'wrong-synthetic-password', accept=False)
        exchange(username=b'', accept=False)
        exchange(username=b'unlisted-synthetic-user', commands=False)
        print('PASS ordinary login, wrong-password rejection, CWE-287 wrong-user acceptance, Telnet NVT', flush=True)
        strict = json.loads(original_auth)
        strict['authentication'] = 'username-and-password'
        auth.write_text(json.dumps(strict))
        exchange(username=b'unlisted-synthetic-user', accept=False)
        exchange(commands=False)
        auth.write_bytes(original_auth)
        auth.chmod(0o644)
        check(not stat.S_IMODE(auth.stat().st_mode) & 0o022, 'Permission control is writable by others')
        exchange(commands=False)
        auth.chmod(auth_mode)
        exchange(malformed=b'A' * 129 + b'\r\n')
        exchange(malformed=b'\x80\r\n')
        print('PASS strict-auth control, bounded malformed input, fixed commands and startup guards', flush=True)
        if external:
            check(isolation_checks[0] > 0, 'No external-interface negative tests')
            print('PASS connections refused on assigned non-loopback IPv4 interfaces', flush=True)
        else:
            print('SKIP non-loopback interface probe: none assigned in this namespace', flush=True)
        print('PASS loopback alias refusal and hard-coded 127.0.0.1 endpoint', flush=True)
        client_bytes = b''.join(bytes.fromhex(item['hex']) for item in records
                                if item['direction'] == 'client-to-service')
        server_bytes = b''.join(bytes.fromhex(item['hex']) for item in records
                                if item['direction'] == 'service-to-client')
        check(USER in client_bytes and PASSWORD in client_bytes and b'STATUS' in client_bytes
              and b'SYNTHETIC STATUS: nominal' in server_bytes, 'Plaintext exchange not observed')
        if transcript_path:
            Path(transcript_path).write_text(json.dumps(records, indent=2) + '\n')
        print('PASS actual socket byte transcript contains plaintext credentials and session data', flush=True)
    finally:
        auth.write_bytes(original_auth)
        auth.chmod(auth_mode)
        manifest.write_bytes(original_build)
        manifest.chmod(build_mode)
        capture.finish(pcap)
    capture.verify()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--isolated-fixture', action='store_true', required=True)
    parser.add_argument('--installed', action='store_true', required=True)
    parser.add_argument('--pcap', type=Path)
    parser.add_argument('--require-pcap', action='store_true')
    parser.add_argument('--transcript', type=Path)
    arguments = parser.parse_args()
    run_tests(Path('/'), arguments.pcap, arguments.require_pcap, arguments.transcript)


if __name__ == '__main__':
    main()
