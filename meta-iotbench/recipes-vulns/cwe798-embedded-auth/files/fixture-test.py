#!/usr/bin/env python3
"""Local guest/host integration checks against the installed socket service."""

import argparse
import contextlib
import json
from pathlib import Path
import runpy
import select
import socket
import subprocess
import sys
import tempfile


@contextlib.contextmanager
def service(root, work):
    runtime = work / 'runtime'
    process = subprocess.Popen([sys.executable, '-B', str(root / 'fixture-service.py'),
                                '--isolated-fixture', '--runtime-dir', str(runtime)],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        readable, _, _ = select.select([process.stdout], [], [], 10)
        if not readable or process.stdout.readline() != b'fixture-ready\n':
            process.terminate()
            _, stderr = process.communicate(timeout=5)
            raise AssertionError('Service did not start: ' + stderr.decode())
        assert (runtime.stat().st_mode & 0o777) == 0o700
        assert ((runtime / 'auth.sock').stat().st_mode & 0o777) == 0o600
        yield runtime / 'auth.sock'
    finally:
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=5)
        process.stdout.close()
        process.stderr.close()
        assert not runtime.exists(), 'Runtime socket/directory not cleaned'


def request(endpoint, data):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(3)
        client.connect(str(endpoint))
        client.sendall(data)
        client.shutdown(socket.SHUT_WR)
        result = bytearray()
        while True:
            block = client.recv(64)
            if not block:
                break
            result.extend(block)
        return bytes(result)


def authenticate(root, work):
    lib = runpy.run_path(str(root / 'fixture-lib.py'))
    config = json.loads((root / 'build-config.json').read_text())
    u, p = lib['read_pair'](root / lib['FILES'][config['variant']], config['variant'])
    good = json.dumps(dict(username=u, password=p)).encode() + b'\n'
    with service(root, work) as endpoint:
        assert request(endpoint, good) == b'OK\n'
        for data in (
                json.dumps(dict(username=u, password='incorrect')).encode() + b'\n',
                json.dumps(dict(username='incorrect', password=p)).encode() + b'\n',
                json.dumps(dict(username='incorrect', password='incorrect')).encode() + b'\n',
                b'{}\n', b'not-json\n', b'', b'x' * 1025,
                b'{"username":"a","username":"b","password":"c"}\n',
                b'{"username":"a","password":"c","extra":1}\n',
                b'{"username":"a\\u0000b","password":"c"}\n',
                b'{"username":42,"password":"c"}\n', good.rstrip(b'\n'),
                b'\xff\n'):
            assert request(endpoint, data) == b'DENIED\n', repr(data)
        assert request(endpoint, good) == b'OK\n', 'Service failed after invalid requests'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--isolated-fixture', action='store_true')
    args = parser.parse_args()
    if not args.isolated_fixture:
        return 77
    with tempfile.TemporaryDirectory(prefix='auth798-') as temp:
        authenticate(Path(__file__).resolve().parent, Path(temp))
    print('PASS embedded pair accepted; incorrect/malformed requests denied; Unix socket cleaned')
    return 0


if __name__ == '__main__':
    sys.exit(main())
