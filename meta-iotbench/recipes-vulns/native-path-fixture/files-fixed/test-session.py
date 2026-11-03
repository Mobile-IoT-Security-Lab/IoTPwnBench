#!/usr/bin/env python3
"""Socket regressions; refuse to run outside the disposable fixture root."""
from contextlib import contextmanager
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import select
import socket
import stat
import struct
import subprocess
import tempfile
import unittest

BASE = Path('/fixture')
INFO = json.loads((BASE / 'variant.json').read_text())
CWE = INFO['cwe']
SANITIZE = json.loads((BASE / 'test-options.json').read_text())['sanitize']
PUBLIC = b'SYNTHETIC_ALLOWED_CONFIGURATION\n'
SENTINEL = b'SYNTHETIC_CWE22_SENTINEL_ONLY\n'
BACKUP = b'SYNTHETIC_CWE20_DISALLOWED_BACKUP\n'
CONTRACT = re.compile(br'[a-z][a-z0-9_-]{0,31}\.cfg\Z')


def frame(data):
    return struct.pack('!H', len(data)) + data


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (os.getuid() != 1000 or os.geteuid() != 1000 or os.getgid() != 1000 or
                Path('/run/iotbench-path-isolated').read_bytes() != b'IOTBENCH_PATH_ISOLATED_V1\n'):
            raise RuntimeError('Tests require the unprivileged namespace runner')
        status = Path('/proc/self/status').read_text()
        for expected in ('CapEff:\t0000000000000000', 'CapPrm:\t0000000000000000', 'NoNewPrivs:\t1'):
            if expected not in status:
                raise RuntimeError('Capabilities/no-new-privileges check failed')
        if os.getpid() != 1 or list(Path('/oldroot').iterdir()):
            raise RuntimeError('Require private PID namespace and detached host root')
        mounts = Path('/proc/self/mountinfo').read_text().splitlines()
        if len(mounts) != 4 or sorted(line.split(' - ')[1].split()[0] for line in mounts) != ['proc', 'tmpfs', 'tmpfs', 'tmpfs']:
            raise RuntimeError('Only the disposable tmpfs root, run, tmp and private proc may be mounted')
        interfaces = Path('/proc/net/dev').read_text().splitlines()[2:]
        if len(interfaces) != 1 or interfaces[0].split(':')[0].strip() != 'lo':
            raise RuntimeError('Unexpected network interface')
        try:
            (BASE / 'fs/write-probe').write_bytes(b'forbidden')
        except OSError as error:
            if error.errno != errno.EROFS:
                raise
        else:
            raise RuntimeError('Synthetic filesystem must be read-only')
        for p in (BASE / 'fs').rglob('*'):
            if p.is_symlink() or not (p.is_dir() or p.is_file()):
                raise RuntimeError('Only ordinary resources are allowed')
        cls.before = cls.snapshot()

    @classmethod
    def snapshot(cls):
        return {str(p): (hashlib.sha256(p.read_bytes()).hexdigest(), stat.S_IMODE(p.stat().st_mode))
                for p in (BASE / 'fs').rglob('*') if p.is_file()}

    @classmethod
    def tearDownClass(cls):
        if cls.snapshot() != cls.before:
            raise AssertionError('Read-only resources changed')
        if Path('/run/path.sock').exists():
            raise AssertionError('Socket cleanup failed')

    @contextmanager
    def service(self, asan=False):
        name = 'fixture-path-cwe' + CWE + ('-asan' if asan else '')
        path = Path('/run/path.sock')
        self.assertFalse(path.exists())
        log = tempfile.TemporaryFile()
        process = subprocess.Popen([str(BASE / 'bin' / name), '--isolated-fixture'],
                                   stdout=subprocess.PIPE, stderr=log)
        try:
            self.assertTrue(select.select([process.stdout], [], [], 10)[0], 'Startup timed out')
            ready = process.stdout.readline()
            if not ready:
                process.wait(timeout=5)
            log.seek(0)
            self.assertEqual(ready, b'fixture-ready unix-only\n', (process.poll(), log.read()))
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)
            status = Path('/proc/' + str(process.pid) + '/status').read_text()
            self.assertIn('Uid:\t1000\t1000\t1000\t1000', status)
            self.assertIn('CapEff:\t0000000000000000', status)
            self.assertIn('NoNewPrivs:\t1', status)
            yield process
            self.assertIsNone(process.poll(), 'Service exited unexpectedly')
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            process.stdout.close()
            log.seek(0)
            errors = log.read()
            log.close()
            if path.exists():
                path.unlink()
            self.assertNotIn(b'AddressSanitizer', errors, errors)
            self.assertNotIn(b'runtime error:', errors, errors)

    def raw(self, wire, fragment=False):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(4)
            client.connect('/run/path.sock')
            chunks = [bytes([value]) for value in wire] if fragment else [wire]
            for chunk in chunks:
                try:
                    client.sendall(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    break  # Oversized declarations can be rejected immediately.
            client.shutdown(socket.SHUT_WR)
            response = b''
            while True:
                try:
                    data = client.recv(8192)
                except ConnectionResetError:
                    break
                if not data:
                    break
                response += data
                self.assertLessEqual(len(response), 4140)
        return response

    def expect_ok(self, name, body, fragment=False):
        self.assertEqual(self.raw(frame(name), fragment), b'OK ' + str(len(body)).encode() + b'\n' + body)

    def cases(self, asan):
        with self.service(asan) as process:
            self.assertIsNotNone(CONTRACT.fullmatch(b'public.cfg'))
            self.expect_ok(b'public.cfg', PUBLIC, fragment=True)
            if CWE == '022':
                sentinel = BASE / 'fs/sentinel.txt'
                self.assertEqual(sentinel.read_bytes(), SENTINEL)
                self.assertTrue(os.access(str(sentinel), os.R_OK))
                self.assertFalse(str(sentinel).startswith(str(BASE / 'fs/allowed') + '/'))
                for name in (b'../sentinel.txt', b'./../sentinel.txt', b'../allowed/../sentinel.txt'):
                    self.assertEqual(self.raw(frame(name)), b'ERR DENIED\n', name)
                self.assertEqual({p.name for p in (BASE / 'fs').iterdir()}, {'allowed', 'sentinel.txt'})
                for name in (b'../../etc/passwd', b'../../proc/self/root/etc/passwd',
                             b'../missing.txt', b'../allowed', b'.', b'..'):
                    self.assertIn(self.raw(frame(name)), (b'ERR DENIED\n', b'ERR MISSING\n'))
            else:
                self.assertIsNone(CONTRACT.fullmatch(b'private.cfg.bak'))
                self.assertEqual((BASE / 'fs/allowed/private.cfg.bak').read_bytes(), BACKUP)
                self.assertEqual(self.raw(frame(b'private.cfg.bak')), b'ERR DENIED\n')
                self.assertEqual({p.name for p in (BASE / 'fs').iterdir()}, {'allowed'})
                for name in (b'../sentinel.txt', b'../allowed/public.cfg', b'./public.cfg',
                             b'private.bak', b'public', b'.cfg', b'1public.cfg',
                             b'a' * 33 + b'.cfg', b'public..cfg', b'public.cfg/other'):
                    self.assertEqual(self.raw(frame(name)), b'ERR DENIED\n', name)
            self.assertEqual(self.raw(frame(b'missing.cfg')), b'ERR MISSING\n')
            self.assertEqual(self.raw(frame(b'a' * 32 + b'.cfg')), b'ERR MISSING\n')
            # Exactly 255 bytes reaches filesystem/policy handling; 256 is a
            # protocol violation. Neither case reads an unintended file.
            self.assertIn(self.raw(frame(b'a' * 255)), (b'ERR DENIED\n', b'ERR MISSING\n'))
            for wire in (b'', b'\0', frame(b''), b'\0\x05abc', frame(b'public.cfg') + b'x',
                         frame(b'/public.cfg'), frame(b'public\0.cfg'), frame(b'public\n.cfg'),
                         frame(b'public\\.cfg'), frame(b'PUBLIC.cfg'), frame(b'%2e%2e'),
                         frame(b'\xff'), frame(b'a' * 256), frame(b'a' * 4096), b'\xff\xff'):
                self.assertEqual(self.raw(wire), b'ERR INVALID\n', repr(wire[:50]))
                self.expect_ok(b'public.cfg', PUBLIC)
            # The process owns one AF_UNIX listener, with no IP sockets.
            sockets = {os.readlink(str(p))[8:-1] for p in Path('/proc/' + str(process.pid) + '/fd').iterdir()
                       if os.readlink(str(p)).startswith('socket:[')}
            self.assertEqual(len(sockets), 1)
            self.assertTrue(any(line.endswith('/run/path.sock') and line.split()[6] in sockets
                                for line in Path('/proc/net/unix').read_text().splitlines()[1:]))
            for protocol in ('tcp', 'tcp6', 'udp', 'udp6'):
                path = Path('/proc/net') / protocol
                if path.exists():
                    self.assertFalse(sockets.intersection(line.split()[9] for line in path.read_text().splitlines()[1:]))

    def test_artifact_service(self):
        self.cases(False)

    @unittest.skipUnless(SANITIZE, 'sanitizer build not requested')
    def test_artifact_asan_service(self):
        self.cases(True)

    def test_runtime_optin_and_existing_socket(self):
        binary = str(BASE / 'bin' / ('fixture-path-cwe' + CWE))
        for args in ([], ['--wrong-mode']):
            result = subprocess.run([binary] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
            self.assertEqual(result.returncode, 77)
            self.assertEqual(result.stdout, b'')
        path = Path('/run/path.sock')
        path.write_bytes(b'SYNTHETIC_EXISTING_PATH\n')
        try:
            result = subprocess.run([binary, '--isolated-fixture'], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=5)
            self.assertEqual(result.returncode, 77)
            self.assertEqual(path.read_bytes(), b'SYNTHETIC_EXISTING_PATH\n')
        finally:
            path.unlink()


if __name__ == '__main__':
    unittest.main(verbosity=2)
