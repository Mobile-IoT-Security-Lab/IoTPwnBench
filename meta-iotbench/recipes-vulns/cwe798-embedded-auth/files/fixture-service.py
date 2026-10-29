#!/usr/bin/env python3
"""Explicitly started local synthetic authentication; no startup integration."""

import argparse
import os
from pathlib import Path
import runpy
import signal
import socket
import sys

LIB = runpy.run_path(str(Path(__file__).resolve().with_name('fixture-lib.py')))


def serve(root, runtime):
    config = LIB['json_object']((root / 'build-config.json').read_text())
    LIB['validate_build'](config['mode'], config['enabled'], config['machine'], config['variant'])
    authenticate = LIB['verifier'](root, config)
    # A freshly created directory prevents symlink/socket replacement. The caller
    # supplies an existing private parent; no pre-existing socket is unlinked.
    parent = runtime.parent
    stat = parent.lstat()
    if parent.is_symlink() or stat.st_uid != os.geteuid() or stat.st_mode & 0o077:
        raise ValueError('Runtime parent must be private and owned by the current user')
    runtime.mkdir(mode=0o700)
    endpoint = runtime / 'auth.sock'
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(str(endpoint))
            endpoint.chmod(0o600)
            server.listen(4)
            print('fixture-ready', flush=True)
            while True:
                connection, _ = server.accept()
                with connection:
                    connection.settimeout(1)
                    accepted = False
                    try:
                        data = bytearray()
                        while b'\n' not in data and len(data) <= 1024:
                            block = connection.recv(min(1025 - len(data), 1024))
                            if not block:
                                break
                            data.extend(block)
                        if len(data) > 1024 or not data.endswith(b'\n') or data.count(b'\n') != 1:
                            raise ValueError('Invalid request framing')
                        u, p = LIB['pair'](LIB['json_object'](data.decode('ascii')))
                        accepted = authenticate(u, p)
                    except (ValueError, UnicodeError, OSError):
                        pass
                    try:
                        connection.sendall(b'OK\n' if accepted else b'DENIED\n')
                    except OSError:
                        pass
    finally:
        if endpoint.exists():
            endpoint.unlink()
        runtime.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--isolated-fixture', action='store_true')
    parser.add_argument('--runtime-dir', required=True, type=Path)
    args = parser.parse_args()
    if not args.isolated_fixture:
        return 77
    def stop(signum, frame):
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, stop)
    try:
        serve(Path(__file__).resolve().parent, args.runtime_dir.absolute())
    except (ValueError, OSError, KeyError) as error:
        print('Fixture configuration refused: ' + str(error), file=sys.stderr)
        return 77
    return 0


if __name__ == '__main__':
    sys.exit(main())
