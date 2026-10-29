#!/usr/bin/env python3
"""INTENTIONALLY INSECURE synthetic Telnet fixture; never an OS login service."""

import argparse
import json
from pathlib import Path
import signal
import socket
import time

DATA = Path('@DATADIR@/iotbench/unencrypted-traffic')
AUTH = Path('@SYSCONFDIR@/iotbench/telnet-auth.json')
FIXTURE_USER = 'telnet-fixture'
FIXTURE_PASSWORD = 'Fixture-Telnet-Only-42'
LOOPBACK = '127.0.0.1'  # Isolation is code, never taken from the writable policy.
MACHINES = ('qemuarm64', 'qemuarm', 'qemux86-64', 'qemux86', 'qemumips')
IAC, DONT, DO, WONT, WILL, SB, SE = 255, 254, 253, 252, 251, 250, 240


def require_test_build():
    build = json.loads((DATA / 'build-config.json').read_text())
    if (build.get('mode') != 'fixture' or build.get('enabled') is not True
            or build.get('machine') not in MACHINES):
        raise ValueError('Refusing non-fixture/production build')


class TelnetLines:
    """Bounded NVT line reader: CRLF/CR-NUL, IAC and option refusal, no terminal."""

    def __init__(self, connection):
        self.connection = connection
        self.after_cr = False
        self.deadline = time.monotonic() + 8
        self.budget = 4096

    def byte(self):
        if time.monotonic() >= self.deadline or self.budget <= 0:
            raise ValueError('Session limit')
        self.budget -= 1
        value = self.connection.recv(1)
        if not value:
            raise EOFError()
        return value[0]

    def line(self):
        result = bytearray()
        while True:
            value = self.byte()
            if value == IAC:
                command = self.byte()
                if command in (DO, DONT, WILL, WONT):
                    option = self.byte()
                    if command in (DO, WILL):
                        reply = WONT if command == DO else DONT
                        self.connection.sendall(bytes((IAC, reply, option)))
                    continue
                if command == SB:
                    previous = None
                    while True:
                        item = self.byte()
                        if previous == IAC and item == SE:
                            break
                        previous = item
                    continue
                if command != IAC:
                    continue
            if self.after_cr:
                self.after_cr = False
                if value in (0, 10):
                    continue
            if value in (10, 13):
                self.after_cr = value == 13
                return result.decode('ascii', errors='strict')
            if value < 32 or value > 126 or len(result) >= 128:
                raise ValueError('Invalid or oversized synthetic input')
            result.append(value)


def authenticated(username, password, policy):
    if policy == 'password-only':
        # CWE-287: deliberately ignores the asserted username (same Telnet scenario).
        return bool(username) and password == FIXTURE_PASSWORD
    return username == FIXTURE_USER and password == FIXTURE_PASSWORD


def session(connection, policy):
    connection.settimeout(3)
    reader = TelnetLines(connection)
    # Refuse option negotiation; all subsequent bytes remain unencrypted NVT data.
    connection.sendall(b'IOTBENCH SYNTHETIC TELNET - TEST ONLY\r\nlogin: ')
    username = reader.line()
    connection.sendall(b'Password: ')
    password = reader.line()
    if not authenticated(username, password, policy):
        connection.sendall(b'Authentication failed\r\n')
        return
    connection.sendall(b'Synthetic authentication accepted\r\nfixture> ')
    for _ in range(8):
        command = reader.line()
        if command == 'QUIT':
            connection.sendall(b'Goodbye fixture\r\n')
            return
        responses = {
            'STATUS': b'SYNTHETIC STATUS: nominal\r\n',
            'HELP': b'STATUS HELP QUIT (predefined responses only)\r\n',
        }
        connection.sendall(responses.get(command, b'Unknown synthetic command\r\n')
                           + b'fixture> ')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture-test', action='store_true')
    parser.add_argument('--port', type=int, default=2323)
    arguments = parser.parse_args()
    if not arguments.fixture_test:
        parser.error('Explicit --fixture-test is required')
    if not 0 <= arguments.port <= 65535:
        parser.error('Invalid port')
    try:
        require_test_build()
        policy = json.loads(AUTH.read_text())
        if set(policy) != {'authentication', 'credential_scope', 'transport'}:
            raise ValueError('Unexpected authentication configuration')
        authentication = policy['authentication']
        if (authentication not in ('password-only', 'username-and-password')
                or policy['credential_scope'] != 'public-synthetic-only'
                or policy['transport'] != 'telnet-plaintext'):
            raise ValueError('Invalid authentication configuration')
    except (OSError, ValueError) as error:
        parser.error(str(error))

    signal.alarm(30)  # Finite one-session test process, also if no client arrives.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind((LOOPBACK, arguments.port))
        listener.listen(1)
        listener.settimeout(10)
        print(json.dumps({'host': LOOPBACK, 'port': listener.getsockname()[1]}), flush=True)
        try:
            connection, peer = listener.accept()
            with connection:
                if peer[0] != LOOPBACK:
                    raise ValueError('Non-loopback peer refused')
                session(connection, authentication)
        except (OSError, EOFError, ValueError):
            # Malformed/disconnected/timed-out synthetic clients get no further access.
            pass


if __name__ == '__main__':
    main()
