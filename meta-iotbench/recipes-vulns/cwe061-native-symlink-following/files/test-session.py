#!/usr/bin/env python3
"""Socket regressions; refuse to run outside the disposable fixture root."""
from contextlib import contextmanager
import errno
import hashlib
import os
from pathlib import Path
import select
import socket
import stat
import struct
import subprocess
import tempfile
import unittest

BASE = Path('/fixture')
PUBLIC = b'SYNTHETIC_CWE61_ORDINARY_CONFIGURATION\n'
SENTINEL = b'SYNTHETIC_CWE61_SENTINEL_ONLY\n'
WORK = Path('/tmp/symlink-fixture')
ENTRY = WORK / 'allowed/public.cfg'


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
        if Path('/run/symlink.sock').exists():
            raise AssertionError('Socket cleanup failed')

    @contextmanager
    def service(self):
        name = 'fixture-symlink-cwe061'
        path = Path('/run/symlink.sock')
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
            client.connect('/run/symlink.sock')
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

    def setUp(self):
        WORK.mkdir(mode=0o700)
        (WORK / 'allowed').mkdir(mode=0o700)
        for name in ('allowed/public.cfg', 'sentinel.txt'):
            (WORK / name).write_bytes((BASE / 'fs' / name).read_bytes())
            (WORK / name).chmod(0o644)
        self.parent_identity = (WORK / 'allowed').stat().st_ino

    def tearDown(self):
        # unlink removes a directory entry, including dangling links; never
        # traverse a link or use resolve()/rmtree() on the attack entry.
        if os.path.lexists(str(ENTRY)):
            ENTRY.unlink()
        self.assertEqual((WORK / 'sentinel.txt').read_bytes(), SENTINEL)
        self.assertEqual((WORK / 'allowed').stat().st_ino, self.parent_identity)
        (WORK / 'sentinel.txt').unlink()
        (WORK / 'allowed').rmdir()
        WORK.rmdir()
        self.assertFalse(os.path.lexists('/run/symlink.sock'))

    def test_ordinary_file(self):
        self.assertFalse(ENTRY.is_symlink())
        self.assertEqual(ENTRY.read_bytes(), PUBLIC)
        self.assertTrue(os.access(str(ENTRY), os.R_OK))
        with self.service():
            self.expect_ok(b'READ', PUBLIC, fragment=True)

    def test_preestablished_symbolic_link(self):
        ENTRY.unlink()
        ENTRY.symlink_to('../sentinel.txt')
        self.assertTrue(ENTRY.is_symlink())
        self.assertEqual(os.readlink(str(ENTRY)), '../sentinel.txt')
        self.assertEqual(ENTRY.stat().st_ino, (WORK / 'sentinel.txt').stat().st_ino)
        self.assertTrue(os.access(str(ENTRY), os.R_OK))
        # The link is in place before process startup and before any request.
        with self.service() as process:
            self.expect_ok(b'READ', SENTINEL)
            before = len(list(Path('/proc/' + str(process.pid) + '/fd').iterdir()))
            for _ in range(20):
                self.expect_ok(b'READ', SENTINEL)
            after = len(list(Path('/proc/' + str(process.pid) + '/fd').iterdir()))
            self.assertEqual(before, after, 'Request descriptors leaked')
        ENTRY.unlink()
        self.assertEqual((WORK / 'sentinel.txt').read_bytes(), SENTINEL)

    def test_missing_file(self):
        ENTRY.unlink()
        with self.service():
            self.assertEqual(self.raw(frame(b'READ')), b'ERR MISSING\n')

    def test_dangling_symbolic_link(self):
        ENTRY.unlink()
        ENTRY.symlink_to('../missing-synthetic.txt')
        self.assertTrue(ENTRY.is_symlink())
        with self.service():
            self.assertEqual(self.raw(frame(b'READ')), b'ERR MISSING\n')

    def test_only_fixed_operation_accepted(self):
        with self.service():
            for wire in (b'', b'\0', frame(b''), b'\0\x04REA', frame(b'READ') + b'x',
                         frame(b'../sentinel.txt'), frame(b'/sentinel.txt'), frame(b'public.cfg'),
                         frame(b'READ ../sentinel.txt'), frame(b'REA\0'), frame(b'READ\n'),
                         frame(b'\xff' * 4), frame(b'x' * 256), b'\xff\xff'):
                self.assertEqual(self.raw(wire), b'ERR INVALID\n', repr(wire[:50]))
                self.expect_ok(b'READ', PUBLIC)

    def test_runtime_optin_and_existing_socket(self):
        binary = str(BASE / 'bin/fixture-symlink-cwe061')
        for args in ([], ['--wrong-mode']):
            result = subprocess.run([binary] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
            self.assertEqual(result.returncode, 77)
            self.assertEqual(result.stdout, b'')
        path = Path('/run/symlink.sock')
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
