#!/usr/bin/env python3
"""Deterministic native REST fixture tests. No TCP, root privileges or network."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import select
import shutil
import socket
import stat
import subprocess
import tempfile
import textwrap
import unittest

# These tests parse tool output as text, so run the tools in the neutral locale.
os.environ["LC_ALL"] = "C"

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / 'meta-iotbench'
SLUG = 'cwe022-rest-internal-files'
SOURCE = LAYER / 'recipes-vulns' / SLUG / 'files'
BUILD = runpy.run_path(str(SOURCE / 'fixture-build.py'))
DEVICES = ('router', 'ipcamera', 'smartplug', 'thermostat', 'plc', 'smartbulb',
           'smarthub', 'envsensor', 'smartspeaker', 'healthmonitor', 'doorlock')
SANITIZE = False


def recipe_python(path, name):
    match = re.search(r'^python ' + re.escape(name) + r'\(\) \{\n(.*?)^\}',
                      path.read_text(), re.M | re.S)
    if not match:
        raise AssertionError('Missing recipe function ' + name)
    return compile(textwrap.dedent(match.group(1)), str(path) + ':' + name, 'exec')


class FixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='rest-')
        cls.base = Path(cls.temporary.name)
        cc = ('cc -fsanitize=address,undefined -fno-sanitize-recover=all '
              '-fno-omit-frame-pointer') if SANITIZE else 'cc'
        cls.fixture = BUILD['stage'](cls.base / 'rootfs', 'fixture', '1', cc=cc)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    @contextmanager
    def service(self, secure=False):
        name = 'fixture-rest-secure' if secure else 'fixture-rest'
        path = self.fixture / 'run/rest.sock'
        log = tempfile.TemporaryFile()
        process = subprocess.Popen([str(self.fixture / 'bin' / name), '--isolated-fixture'],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=log)
        try:
            self.assertTrue(select.select([process.stdout], [], [], 5)[0], 'Service startup timed out')
            ready = process.stdout.readline()
            if ready != b'fixture-ready unix-only\n':
                log.seek(0)
                self.fail('Service refused fixture (Linux openat2 is required): ' +
                          repr(ready) + repr(log.read()))
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)
            yield process, log
            self.assertIsNone(process.poll(), 'Service exited after a request')
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            process.stdout.close()
            log.close()
            if path.exists():
                path.unlink()

    def raw(self, request, fragments=None):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(3)
            client.connect(str(self.fixture / 'run/rest.sock'))
            for chunk in fragments or [request]:
                client.sendall(chunk)
            client.shutdown(socket.SHUT_WR)
            response = b''
            while True:
                try:
                    chunk = client.recv(8192)
                except ConnectionResetError:
                    break  # A rejected oversize request can leave unread bytes.
                if not chunk:
                    break
                response += chunk
        header, body = response.split(b'\r\n\r\n', 1)
        code = int(header.split(b' ', 2)[1])
        self.assertIn(b'Connection: close', header)
        length = re.search(br'Content-Length: (\d+)', header).group(1)
        self.assertEqual(len(body), int(length))
        return code, body

    def request(self, file='config.cfg', endpoint='/api/config', method='GET'):
        if method == 'POST':
            body = ('file=' + file).encode()
            request = (method + ' ' + endpoint + ' HTTP/1.1\r\nHost: fixture\r\n'
                       'Content-Type: application/x-www-form-urlencoded\r\n'
                       'Content-Length: ' + str(len(body)) + '\r\n\r\n').encode() + body
        else:
            request = (method + ' ' + endpoint + '?file=' + file +
                       ' HTTP/1.1\r\nHost: fixture\r\n\r\n').encode()
        return self.raw(request)

    def test_ordinary_requests_and_single_vulnerable_route(self):
        expected = (SOURCE / 'assets/api/config.cfg').read_bytes()
        marker = (SOURCE / 'assets/restricted/marker.txt').read_bytes()
        with self.service() as (_, log):
            self.assertEqual(self.request(), (200, expected))
            self.assertEqual(self.request('status.cfg', '/api/status'),
                             (200, (SOURCE / 'assets/api/status.cfg').read_bytes()))
            self.assertEqual(self.request(endpoint='/api/config/read', method='POST'), (200, expected))
            self.assertEqual(self.request('missing.cfg')[0], 404)
            self.assertEqual(self.request('../restricted/marker.txt'), (200, marker))
            self.assertEqual(self.request('%2e%2e%2frestricted%2fmarker.txt'), (200, marker))
            self.assertEqual(self.request('../restricted/marker.txt', '/api/status')[0], 403)
            self.assertEqual(self.request('../restricted/marker.txt', '/api/config/read', 'POST')[0], 403)
            log.seek(0)
            self.assertIn(b'fixture-read path=api/../restricted/marker.txt result=opened', log.read())
        with self.service(secure=True) as (_, log):
            self.assertEqual(self.request(), (200, expected))
            for value in ('../restricted/marker.txt', '%2e%2e%2frestricted%2fmarker.txt',
                          './config.cfg', '/config.cfg', '..', '.'):
                self.assertEqual(self.request(value)[0], 403, value)
            log.seek(0)
            self.assertNotIn(b'restricted', log.read(), 'Secure control must reject before the sink')

    def test_outer_boundary_symlinks_mountlike_paths_and_special_files(self):
        canary = self.base / 'outside-canary.txt'
        canary.write_bytes(b'SYNTHETIC_OUTSIDE_ROOT_MUST_NOT_BE_READ\n')
        link = self.fixture / 'fs/api/link.cfg'
        link.symlink_to(canary)
        fifo = self.fixture / 'fs/api/fifo.cfg'
        os.mkfifo(str(fifo), 0o600)
        directory = self.fixture / 'fs/api/nested'
        directory.mkdir()
        large = self.fixture / 'fs/api/large.cfg'
        large.write_bytes(b'x' * 4097)
        self.addCleanup(link.unlink)
        self.addCleanup(fifo.unlink)
        self.addCleanup(directory.rmdir)
        self.addCleanup(large.unlink)
        with self.service():
            values = ['link.cfg', 'fifo.cfg', 'nested', 'large.cfg',
                      '../../outside-canary.txt', '../../' + str(canary).lstrip('/'),
                      str(canary), '../..', '..//../outside-canary.txt',
                      '../../proc/self/root' + str(canary)]
            for value in values:
                code, body = self.request(value)
                self.assertIn(code, (403, 404), value)
                self.assertNotIn(canary.read_bytes(), body)
            self.assertEqual(self.request()[0], 200)
        self.assertEqual(canary.read_bytes(), b'SYNTHETIC_OUTSIDE_ROOT_MUST_NOT_BE_READ\n')

    def test_malformed_http_and_unsupported_methods(self):
        malformed = [b'', b'GET\r\n\r\n', b'GET /api/config?file=config.cfg HTTP/9.9\r\n\r\n',
                     b'GET / HTTP/1.1\r\nBad Header\r\n\r\n',
                     b'GET / HTTP/1.1\r\nTransfer-Encoding: chunked\r\n\r\n',
                     b'GET / HTTP/1.1\r\nContent-Length: -1\r\n\r\n',
                     b'GET / HTTP/1.1\r\nContent-Length: 0\r\nContent-Length: 0\r\n\r\n',
                     b'GET / HTTP/1.1\r\nContent-Length: 99999999999999999999\r\n\r\n',
                     b'GET / HTTP/1.1\r\nHost: bad\x00value\r\n\r\n',
                     b'GET / HTTP/1.1\r\nHost: ' + b'a' * 4096,
                     b'POST /api/config/read HTTP/1.1\r\nContent-Length: 5\r\n\r\nfile=',
                     b'POST /api/config/read HTTP/1.1\r\nContent-Length: 2\r\n'
                     b'Content-Type: application/x-www-form-urlencoded\r\n\r\nx',
                     b'GET /api/config?file=config.cfg HTTP/1.1\r\nContent-Length: 1\r\n\r\nx',
                     b'GET /api/config?file=config.cfg HTTP/1.1\r\n\r\nGET / HTTP/1.1\r\n\r\n']
        with self.service():
            for value in malformed:
                self.assertEqual(self.raw(value)[0], 400, repr(value[:120]))
                self.assertEqual(self.request()[0], 200)
            for value in ('', '%', '%2', '%GG', '%00', '%0d%0a', '%ff', '%252e%252e',
                          'config.cfg&file=status.cfg', 'config.cfg&x=1', 'x' * 256,
                          '..%5crestricted%5cmarker.txt'):
                self.assertEqual(self.request(value)[0], 400, value)
            for method in ('PUT', 'DELETE', 'PATCH', 'CONNECT', 'TRACE', 'OPTIONS', 'HEAD'):
                self.assertEqual(self.request(method=method)[0], 405)
            for route in ('/api/upload', '/api/config/write', '/api/exec', '/unknown'):
                self.assertEqual(self.request(endpoint=route)[0], 404)
            fragments = [b'POST /api/config/read HTTP/1.1\r\nHost: fixture\r\n',
                         b'Content-Length: 15\r\nContent-Type: application/x-www-form-urlencoded\r\n',
                         b'\r\nfile=', b'config.cfg']
            self.assertEqual(self.raw(None, fragments)[0], 200)

    def test_readonly_no_upload_or_commands_and_only_unix_listener(self):
        def snapshot():
            return {str(p): (hashlib.sha256(p.read_bytes()).hexdigest(),
                             stat.S_IMODE(p.stat().st_mode))
                    for p in (self.fixture / 'fs').rglob('*') if p.is_file()}
        before = snapshot()
        with self.service() as (process, _):
            sockets = {os.readlink(str(p))[8:-1] for p in Path('/proc/' + str(process.pid) + '/fd').iterdir()
                       if os.readlink(str(p)).startswith('socket:[')}
            self.assertEqual(len(sockets), 1)
            unix = Path('/proc/net/unix').read_text().splitlines()
            self.assertTrue(any(line.split()[6] in sockets and
                                line.endswith(str(self.fixture / 'run/rest.sock')) for line in unix[1:]))
            for protocol in ('tcp', 'tcp6', 'udp', 'udp6'):
                path = Path('/proc/net') / protocol
                if path.exists():
                    self.assertFalse(sockets.intersection(line.split()[9] for line in path.read_text().splitlines()[1:]))
            for value in ('config.cfg;touch%20SHOULD_NOT_EXIST', '$(touch%20SHOULD_NOT_EXIST)',
                          '`touch%20SHOULD_NOT_EXIST`', 'config.cfg|id', 'config.cfg%26id'):
                self.assertEqual(self.request(value)[0], 400)
            self.assertEqual(self.request(endpoint='/api/upload', method='POST')[0], 404)
            self.assertEqual(self.request(endpoint='/api/config/write', method='POST')[0], 404)
            self.assertEqual(self.request(endpoint='/api/exec', method='POST')[0], 404)
            self.assertEqual(self.request(endpoint='/api/config/read', method='POST')[0], 200)
        self.assertEqual(snapshot(), before)
        self.assertFalse(list(self.fixture.rglob('SHOULD_NOT_EXIST')))

    def test_runtime_optin_manifest_and_production_stub(self):
        helper = self.fixture / 'bin/fixture-rest'
        def invoke(binary, args=()):
            result = subprocess.run([str(binary)] + list(args), stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=5)
            self.assertEqual(result.returncode, 77)
            self.assertEqual(result.stdout, b'')
            self.assertFalse((self.fixture / 'run/rest.sock').exists())
        invoke(helper)
        invoke(helper, ['--root', str(self.base)])
        output = self.base / 'cli-production'
        result = subprocess.run(['python3', str(ROOT / 'scripts/build-rest-fixture.py'),
                                 '--output', str(output)], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(output.exists())
        marker = self.fixture / 'fs/.fixture-test-only'
        original = marker.read_bytes()
        try:
            marker.write_bytes(b'production\n')
            invoke(helper, ['--isolated-fixture'])
            marker.write_bytes(original)
            marker.chmod(0o666)
            invoke(helper, ['--isolated-fixture'])
            marker.chmod(0o644)
            marker.unlink()
            marker.symlink_to(self.fixture / 'fs/api/config.cfg')
            invoke(helper, ['--isolated-fixture'])
        finally:
            marker.unlink()
            marker.write_bytes(original)
            marker.chmod(0o644)
        for flags in ([], ['-DIOTBENCH_REST_FIXTURE_ENABLED=0']):
            binary = self.base / 'production-stub'
            subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror'] + flags +
                           [str(SOURCE / 'fixture-rest.c'), '-o', str(binary)], check=True)
            invoke(binary, ['--isolated-fixture'])
            self.assertNotIn(b'/api/config', binary.read_bytes())
        # A pre-existing path must never be replaced, including a symlink.
        existing = self.fixture / 'run/rest.sock'
        existing.symlink_to(marker)
        try:
            result = subprocess.run([str(helper), '--isolated-fixture'], timeout=5,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(result.returncode, 77)
            self.assertTrue(existing.is_symlink())
            self.assertEqual(marker.read_bytes(), original)
        finally:
            existing.unlink()

    def test_static_source_sink_and_compiler_protections(self):
        source = (SOURCE / 'fixture-rest.c').read_text()
        # Deterministic structural data-flow check, not a general C taint engine.
        checks = [r'extract_file_parameter\(form, file\)',
                  r'read_internal_file\(rootfd, file, vulnerable, body, &size\)',
                  r'snprintf\(path, sizeof\(path\), "api/%s", file\)',
                  r'confined_open\(rootfd, path, 0\)',
                  r'syscall\(SYS_openat2, rootfd, path, &how, sizeof\(how\)\)',
                  r'if \(!vulnerable && !safe_basename\(file\)\) return 403;',
                  r'vulnerable = !REST_SECURE_CONTROL && !strcmp\(target, "/api/config"\)']
        for check in checks:
            self.assertRegex(source, check)
        self.assertNotRegex(source, r'\b(system|popen|execv\w*|chmod|chown)\s*\(')
        self.assertNotRegex(source, r'\b(O_WRONLY|O_RDWR|O_CREAT|O_TRUNC|AF_INET6?)\b')
        self.assertNotIn('RESOLVE_BENEATH | RESOLVE_NO_SYMLINKS | RESOLVE_NO_XDEV',
                         source[:source.index('#else')])
        manifest = json.loads((SOURCE / 'ground-truth.json').read_text())
        self.assertEqual(manifest['intentional_vulnerabilities'], 1)
        self.assertEqual(manifest['cwes'], ['CWE-22', 'CWE-73'])
        for name in ('fixture-rest', 'fixture-rest-secure'):
            binary = self.fixture / 'bin' / name
            header = subprocess.check_output(['readelf', '-h', str(binary)]).decode()
            self.assertRegex(header, r'Type:\s+DYN')
            program = subprocess.check_output(['readelf', '-W', '-l', str(binary)]).decode()
            self.assertIn('GNU_RELRO', program)
            stack = next(line for line in program.splitlines() if 'GNU_STACK' in line)
            self.assertNotIn('RWE', stack)
            symbols = subprocess.check_output(['readelf', '-Ws', str(binary)]).decode()
            self.assertIn('__stack_chk_fail', symbols)

    def test_device_matrix_guards_target_staging_and_permissions(self):
        common = LAYER / 'recipes-images/iotbench-rest-internal-files.inc'
        package = SOURCE.parent / (SLUG + '_1.0.bb')
        class BB:
            class parse:
                SkipRecipe = ValueError

                @staticmethod
                def mark_dependency(data, path):
                    assert Path(path).is_file()

            @staticmethod
            def fatal(message):
                raise ValueError(message)

        class Metadata:
            def __init__(self, mode='fixture', enabled='1', machine='qemuarm64'):
                self.values = {'IOTBENCH_BUILD_MODE': mode, 'IOTBENCH_ENABLE_REST_FIXTURE': enabled,
                               'MACHINE': machine, 'THISDIR': str(SOURCE.parent),
                               'IOTBENCH_REST_LAYER': str(LAYER), 'IOTBENCH_VULN_INSTALL': SLUG, 'IOTBENCH_TWIN_SUFFIX': '',
                               'IMAGE_INSTALL': 'device-router ' + SLUG}

            def getVar(self, key):
                return self.values.get(key)

        guards = [recipe_python(package, '__anonymous'),
                  recipe_python(common, 'iotbench_rest_fixture_guard')]
        for mode in ('production', 'fixture', None):
            for enabled in ('0', '1', None):
                for machine in BUILD['MACHINES'] + ('production-board', None):
                    valid = mode == 'fixture' and enabled == '1' and machine in BUILD['MACHINES']
                    for code in guards:
                        data = Metadata(mode, enabled, machine)
                        if valid:
                            exec(code, {'d': data, 'bb': BB})
                        else:
                            with self.assertRaises(ValueError):
                                exec(code, {'d': data, 'bb': BB})
                    if not valid:
                        output = self.base / 'forbidden-stage'
                        with self.assertRaises(ValueError):
                            BUILD['stage'](output, mode, enabled, machine)
                        self.assertFalse(output.exists())
        for device in DEVICES:
            image = LAYER / 'recipes-images' / ('iotbench-' + device + '-' + SLUG + '.bb')
            content = image.read_text()
            self.assertIn('require recipes-images/iotbench-image.inc', content)
            self.assertIn('require recipes-devices/{0}/device-{0}.inc'.format(device), content)
            self.assertIn('require recipes-images/iotbench-rest-internal-files.inc', content)
            self.assertNotIn('IOTBENCH_VULN_INSTALL', content)
        for key, value in (('IOTBENCH_VULN_INSTALL', SLUG + ' cwe-other'),
                           ('IMAGE_INSTALL', SLUG + ' cwe-other')):
            data = Metadata()
            data.values[key] = value
            with self.assertRaises(ValueError):
                exec(guards[1], {'d': data, 'bb': BB})
        for machine in BUILD['MACHINES']:
            target = BUILD['stage'](self.base / machine, 'fixture', '1', machine,
                                    binary_dir=self.fixture / 'bin', target_paths=True)
            self.assertEqual((target / 'fs/api/config.cfg').read_bytes(),
                             (SOURCE / 'assets/api/config.cfg').read_bytes())
            for p in [target] + list(target.rglob('*')):
                wanted = 0o755 if p.is_dir() or p.parent == target / 'bin' else 0o644
                if p == target / 'run':
                    wanted = 0o700
                self.assertFalse(p.is_symlink())
                self.assertEqual(stat.S_IMODE(p.stat().st_mode), wanted, str(p))
            self.assertEqual(list((target / 'run').iterdir()), [])
        self.assertNotIn('SECURITY_CFLAGS', package.read_text())
        self.assertNotIn('-fno-stack-protector', package.read_text())

        # Model local-file unpacking from the actual SRC_URI, then use its copy
        # of the same builder as do_install. This catches missing nested assets.
        unpack = self.base / 'unpack'
        unpack.mkdir()
        uri = re.search(r'SRC_URI = "(.*?)"', package.read_text(), re.S).group(1)
        for item in uri.replace('\\\n', ' ').split():
            self.assertTrue(item.startswith('file://'))
            source = SOURCE / item[7:]
            if source.is_dir():
                shutil.copytree(str(source), str(unpack / source.name))
            else:
                shutil.copy2(str(source), str(unpack / source.name))
        staged = runpy.run_path(str(unpack / 'fixture-build.py'))['stage'](
            self.base / 'package-stage', 'fixture', '1', 'qemuarm64',
            binary_dir=self.fixture / 'bin', target_paths=True)
        self.assertEqual((staged / 'fs/restricted/marker.txt').read_bytes(),
                         (SOURCE / 'assets/restricted/marker.txt').read_bytes())

    def test_build_wrapper_and_catalog(self):
        sandbox = self.base / 'wrapper'
        sandbox.mkdir()
        log = sandbox / 'calls'
        docker = sandbox / 'docker'
        docker.write_text('#!/bin/sh\nprintf "%s|%s\\n" "$FIRMWARE" "$*" >> "$FIXTURE_CALLS"\n')
        docker.chmod(0o755)
        env = {k: v for k, v in os.environ.items() if not k.startswith('IOTBENCH_')}
        env.update(PATH=str(sandbox) + ':' + os.environ['PATH'], FIXTURE_CALLS=str(log), MACHINES='qemuarm64')
        def catalog(extra):
            log.write_text('')
            subprocess.run(['sh', str(ROOT / 'scripts/build-all.sh')], env=dict(env, **extra),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=30)
            return [line for line in log.read_text().splitlines() if SLUG in line]
        self.assertEqual(catalog({}), [])
        selected = catalog({'IOTBENCH_ENABLE_REST_FIXTURE': '1'})
        self.assertEqual(len(selected), len(DEVICES))
        self.assertTrue(all('-e IOTBENCH_ENABLE_REST_FIXTURE=1' in call and
                            '-e IOTBENCH_BUILD_MODE=fixture' in call for call in selected))
        bootstrap = sandbox / 'bootstrap.sh'
        bootstrap.write_text(':\n')
        wrapper = sandbox / 'wrapper.sh'
        wrapper.write_text((ROOT / 'scripts/container-build-and-export.sh').read_text().replace(
            'source /opt/yocto/yocto-env.sh', 'source ' + str(bootstrap)))
        bitbake = sandbox / 'bitbake'
        bitbake.write_text('#!/usr/bin/env python3\nimport json, os, pathlib, sys\n'
                           'args = sys.argv[1:]\n'
                           'conf = pathlib.Path(args[1]) if args[0] == "-r" else None\n'
                           'pathlib.Path(os.environ["FIXTURE_CALLS"]).write_text(json.dumps('
                           '{"args": args, "config": conf.read_text() if conf else None}))\n'
                           'sys.exit(39)\n')
        bitbake.chmod(0o755)
        fixture = {'FIRMWARE': 'router-' + SLUG, 'IOTBENCH_ENABLE_REST_FIXTURE': '1'}
        result = subprocess.run(['bash', str(wrapper)], env=dict(env, **fixture),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        self.assertEqual(result.returncode, 39, result.stderr)
        recorded = json.loads(log.read_text())
        self.assertEqual(recorded['config'], 'IOTBENCH_BUILD_MODE = "fixture"\nIOTBENCH_ENABLE_REST_FIXTURE = "1"\n')
        self.assertFalse(Path(recorded['args'][1]).exists())
        invalid = [{'IOTBENCH_BUILD_MODE': 'production'}, {'FIRMWARE': 'router-cwe190-integer-overflow'}]
        invalid += [{flag: '1'} for flag in ('IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE',
                                           'IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE',
                                           'IOTBENCH_ENABLE_SUDO_ENV_FIXTURE',
                                           'IOTBENCH_ENABLE_TELNET_FIXTURE',
                                           'IOTBENCH_ENABLE_FTP_WRITE_FIXTURE')]
        for overrides in invalid:
            log.write_text('not called')
            result = subprocess.run(['bash', str(wrapper)], env=dict(env, **dict(fixture, **overrides)),
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(log.read_text(), 'not called')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--isolated-fixture', action='store_true', required=True)
    parser.add_argument('--sanitize', action='store_true')
    SANITIZE = parser.parse_args().sanitize
    unittest.main(argv=[__file__], verbosity=2)
