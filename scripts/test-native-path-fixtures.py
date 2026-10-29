#!/usr/bin/env python3
"""Build integration and artifact socket tests for the isolated C path fixtures."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / 'meta-iotbench'
FILES = LAYER / 'recipes-vulns/native-path-fixture/files'
BUILD = runpy.run_path(str(FILES / 'fixture-build.py'))
VARIANTS = {'022': 'cwe022-native-path-traversal', '020': 'cwe020-native-filename-validation'}
SANITIZE = False


def function(path, name):
    match = re.search(r'^python ' + re.escape(name) + r'\(\) \{\n(.*?)^\}', path.read_text(), re.M | re.S)
    if not match:
        raise AssertionError('Missing recipe function ' + name)
    return compile(textwrap.dedent(match.group(1)), str(path) + ':' + name, 'exec')


class BB:
    @staticmethod
    def fatal(message):
        raise ValueError(message)

    class parse:
        SkipRecipe = ValueError

        @staticmethod
        def mark_dependency(data, path):
            assert Path(path).is_file()


class Data:
    def __init__(self, cwe='022', mode='fixture', enable='1', machine='qemuarm64'):
        self.values = {'IOTBENCH_BUILD_MODE': mode, 'IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE': enable,
                       'MACHINE': machine, 'THISDIR': str(FILES.parent), 'IOTBENCH_PATH_LAYER': str(LAYER),
                       'PATH_FIXTURE_CWE': cwe, 'PATH_FIXTURE_PACKAGE': VARIANTS[cwe],
                       'IOTBENCH_VULN_INSTALL': VARIANTS[cwe],
                       'IMAGE_INSTALL': 'packagegroup-core-boot ' + VARIANTS[cwe]}

    def getVar(self, key):
        return self.values.get(key)


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='native-path-')
        cls.base = Path(cls.temporary.name)
        cls.artifacts = {cwe: BUILD['stage'](cls.base / cwe, cwe, 'fixture', '1', sanitize=SANITIZE)
                         for cwe in VARIANTS}

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_compiled_artifacts_through_isolated_socket(self):
        for cwe, artifact in self.artifacts.items():
            with self.subTest(cwe=cwe):
                subprocess.run([sys.executable, str(artifact / 'fixture-runner.py'),
                                '--isolated-fixture'] + (['--sanitize'] if SANITIZE else []),
                               check=True, timeout=120)

    def test_production_and_mixed_builds_rejected(self):
        package = function(FILES.parent / 'native-path-fixture.inc', '__anonymous')
        image = function(LAYER / 'recipes-images/iotbench-native-path-fixture.inc', 'iotbench_native_path_guard')
        for cwe in VARIANTS:
            for mode in ('fixture', 'production', None):
                for enable in ('1', '0', None):
                    for machine in BUILD['MACHINES'] + ('production-board', None):
                        valid = mode == 'fixture' and enable == '1' and machine in BUILD['MACHINES']
                        for code in (package, image):
                            data = Data(cwe, mode, enable, machine)
                            if valid:
                                exec(code, {'d': data, 'bb': BB})
                            else:
                                with self.assertRaises(ValueError):
                                    exec(code, {'d': data, 'bb': BB})
                        if not valid:
                            output = self.base / 'must-not-exist'
                            with self.assertRaises(ValueError):
                                BUILD['stage'](output, cwe, mode, enable, machine)
                            self.assertFalse(output.exists())
            for key in ('IMAGE_INSTALL', 'IOTBENCH_VULN_INSTALL', 'PATH_FIXTURE_PACKAGE'):
                data = Data(cwe)
                data.values[key] += ' cwe-other'
                with self.assertRaises(ValueError):
                    exec(image, {'d': data, 'bb': BB})
        for flags in ([], ['-DIOTBENCH_PATH_FIXTURE_ENABLED=0']):
            output = self.base / 'production-stub'
            subprocess.run(['cc'] + BUILD['HARDEN'] + flags +
                           [str(FILES / 'fixture-path.c'), '-o', str(output)], check=True)
            result = subprocess.run([str(output), '--isolated-fixture'], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=5)
            self.assertEqual(result.returncode, 77)
            self.assertNotIn(b'/fixture/fs', output.read_bytes())
        for artifact in self.artifacts.values():
            name = 'fixture-path-cwe' + json.loads((artifact / 'variant.json').read_text())['cwe']
            result = subprocess.run([str(artifact / 'bin' / name), '--isolated-fixture'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
            self.assertEqual(result.returncode, 77, 'Enabled service must refuse the host root')

    def test_device_matrix_and_binary_staging(self):
        for device in BUILD['DEVICES']:
            for cwe, package in VARIANTS.items():
                path = LAYER / 'recipes-images' / ('iotbench-' + device + '-' + package + '.bb')
                content = path.read_text()
                self.assertIn('require recipes-images/iotbench-image.inc', content)
                self.assertIn('require recipes-devices/{0}/device-{0}.inc'.format(device), content)
                self.assertIn('require recipes-images/iotbench-native-path-fixture.inc', content)
                self.assertIn('PATH_FIXTURE_CWE = "' + cwe + '"', content)
                self.assertIn('PATH_FIXTURE_PACKAGE = "' + package + '"', content)
                self.assertIn('PATH_FIXTURE_CWE = "' + cwe + '"',
                              (FILES.parent / (package + '_1.0.bb')).read_text())
        package_text = (FILES.parent / 'native-path-fixture.inc').read_text()
        unpack = self.base / 'unpack'
        unpack.mkdir()
        # Stage from the actual SRC_URI, catching missing nested resource files.
        uri = re.search(r'SRC_URI = "(.*?)"', package_text, re.S).group(1)
        for item in uri.replace('\\\n', ' ').split():
            self.assertTrue(item.startswith('file://'))
            path = FILES / item[7:]
            if path.is_dir():
                shutil.copytree(str(path), str(unpack / path.name))
            else:
                shutil.copyfile(str(path), str(unpack / path.name))
        stage = runpy.run_path(str(unpack / 'fixture-build.py'))['stage']
        for cwe, artifact in self.artifacts.items():
            for machine in BUILD['MACHINES']:
                output = stage(self.base / ('target-' + cwe + '-' + machine), cwe,
                               'fixture', '1', machine, binary_dir=artifact / 'bin', sanitize=SANITIZE)
                info = json.loads((output / 'variant.json').read_text())
                self.assertEqual(info['binary_origin'], 'target')
                for name, digest in info['sha256'].items():
                    self.assertEqual((output / 'bin' / name).read_bytes(), (artifact / 'bin' / name).read_bytes())
                    self.assertEqual(hashlib.sha256((output / 'bin' / name).read_bytes()).hexdigest(), digest)
                resources = {str(p.relative_to(output / 'fs')) for p in (output / 'fs').rglob('*') if p.is_file()}
                self.assertEqual(resources, {'allowed/public.cfg', 'sentinel.txt'} if cwe == '022'
                                 else {'allowed/public.cfg', 'allowed/private.cfg.bak'})
                for p in [output] + list(output.rglob('*')):
                    self.assertFalse(p.is_symlink())
                    expected = 0o755 if p.is_dir() or p.parent == output / 'bin' else 0o644
                    self.assertEqual(p.stat().st_mode & 0o7777, expected)
        self.assertNotIn('SECURITY_CFLAGS =', package_text)
        self.assertNotIn('-fno-stack-protector', package_text)
        self.assertNotIn('INITSCRIPT', package_text)
        self.assertIn('INHIBIT_PACKAGE_STRIP = "1"', package_text)
        self.assertIn('INHIBIT_PACKAGE_DEBUG_SPLIT = "1"', package_text)

    def test_binary_hardening_and_variant_classifications(self):
        truth = json.loads((FILES / 'ground-truth.json').read_text())['variants']
        self.assertEqual(truth['022']['primary_cwe'], 'CWE-22')
        self.assertEqual(truth['022']['contributing_cwes'], ['CWE-20'])
        self.assertEqual(truth['020']['primary_cwe'], 'CWE-20')
        for cwe, artifact in self.artifacts.items():
            self.assertEqual(truth[cwe]['intentional_vulnerabilities'], 1)
            for path in (artifact / 'bin').iterdir():
                header = subprocess.check_output(['readelf', '-h', str(path)]).decode()
                self.assertRegex(header, r'Type:\s+DYN')
                program = subprocess.check_output(['readelf', '-W', '-l', str(path)]).decode()
                self.assertIn('GNU_RELRO', program)
                self.assertNotIn('RWE', next(line for line in program.splitlines() if 'GNU_STACK' in line))
                dynamic = subprocess.check_output(['readelf', '-d', str(path)]).decode()
                self.assertIn('BIND_NOW', dynamic)
                symbols = subprocess.check_output(['readelf', '-Ws', str(path)]).decode()
                self.assertIn('__stack_chk_fail', symbols)
            binary = (artifact / 'bin' / ('fixture-path-cwe' + cwe)).read_bytes()
            self.assertIn(b'allowed/%s' if cwe == '022' else b'.cfg', binary)
            self.assertNotIn(b'.cfg' if cwe == '022' else b'allowed/%s', binary)

    def test_rootfs_metadata_and_integrity(self):
        metadata = LAYER / 'recipes-images/iotbench-native-path-fixture.inc'
        # A root-mapped user namespace models pseudo's root ownership without
        # granting host root privileges or executing any vulnerable service.
        driver = self.base / 'metadata-check.py'
        driver.write_text('import json, re, sys, textwrap\n'
                          'from pathlib import Path\n'
                          'class Data:\n'
                          '    def getVar(self, key): return values.get(key)\n'
                          'class BB:\n'
                          '    @staticmethod\n'
                          '    def fatal(message): raise ValueError(message)\n'
                          'values = json.loads(sys.argv[2])\n'
                          'source = re.search(r"^python iotbench_native_path_metadata\\(\\) \\{\\n(.*?)^\\}", '
                          'Path(sys.argv[1]).read_text(), re.M | re.S).group(1)\n'
                          'exec(compile(textwrap.dedent(source), sys.argv[1], "exec"), {"d": Data(), "bb": BB})\n')
        for cwe, artifact in self.artifacts.items():
            output = self.base / ('rootfs-' + cwe)
            staged = BUILD['stage'](output, cwe, 'fixture', '1', binary_dir=artifact / 'bin', sanitize=SANITIZE)
            manifest = output / 'image.manifest'
            manifest.write_text(VARIANTS[cwe] + ' qemuarm64 1.0\n')
            data = Data(cwe)
            data.values.update(IMAGE_ROOTFS=str(output), IMAGE_MANIFEST=str(manifest), datadir='/usr/share')

            def check(success=True):
                result = subprocess.run(['unshare', '--user', '--map-root-user', sys.executable,
                                         str(driver), str(metadata), json.dumps(data.values)],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
                if success:
                    self.assertEqual(result.returncode, 0, result.stderr)
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(b'ValueError:', result.stderr)

            for device in BUILD['DEVICES']:
                data.values['IOTBENCH_DEVICE'] = device
                check()
                for name in ('device.conf', 'peripherals.conf'):
                    self.assertEqual((output / 'etc/iotbench' / name).read_bytes(),
                                     (LAYER / 'recipes-devices' / device / 'files' / name).read_bytes())
            binary = staged / 'bin' / ('fixture-path-cwe' + cwe)
            original = binary.read_bytes()
            binary.write_bytes(original + b'tampered')
            check(False)
            binary.write_bytes(original)
            resource = staged / 'fs/allowed/public.cfg'
            resource.chmod(0o666)
            check(False)
            resource.chmod(0o644)
            manifest.write_text(VARIANTS[cwe] + ' qemuarm64 1.0\ncwe-other qemuarm64 1.0\n')
            check(False)
            manifest.write_text(VARIANTS[cwe] + ' qemuarm64 1.0\n')
            check()

    def test_build_wrappers_and_qemu_exclusion(self):
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
            return [line for line in log.read_text().splitlines() if any(p in line for p in VARIANTS.values())]

        self.assertEqual(catalog({}), [])
        selected = catalog({'IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE': '1'})
        self.assertEqual(len(selected), 22)
        self.assertTrue(all('-e IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE=1' in line and
                            '-e IOTBENCH_BUILD_MODE=fixture' in line for line in selected))
        bootstrap = sandbox / 'bootstrap.sh'
        bootstrap.write_text(':\n')
        wrapper = sandbox / 'wrapper.sh'
        wrapper.write_text((ROOT / 'scripts/container-build-and-export.sh').read_text().replace(
            'source /opt/yocto/yocto-env.sh', 'source ' + str(bootstrap)))
        bitbake = sandbox / 'bitbake'
        bitbake.write_text('#!' + sys.executable + '\nimport json, os, pathlib, sys\n'
                           'args = sys.argv[1:]\nconf = pathlib.Path(args[1]) if args[0] == "-r" else None\n'
                           'pathlib.Path(os.environ["FIXTURE_CALLS"]).write_text(json.dumps('
                           '{"args": args, "config": conf.read_text() if conf else None}))\n'
                           'sys.exit(39)\n')
        bitbake.chmod(0o755)
        for slug in VARIANTS.values():
            settings = {'FIRMWARE': 'router-' + slug, 'IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE': '1'}
            result = subprocess.run(['bash', str(wrapper)], env=dict(env, **settings),
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            self.assertEqual(result.returncode, 39, result.stderr)
            call = json.loads(log.read_text())
            self.assertEqual(call['config'], 'IOTBENCH_BUILD_MODE = "fixture"\nIOTBENCH_ENABLE_NATIVE_PATH_FIXTURE = "1"\n')
            self.assertFalse(Path(call['args'][1]).exists())
            result = subprocess.run(['bash', str(wrapper)], env=dict(env, **dict(settings, IOTBENCH_NATIVE_PATH_ASAN='1')),
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            self.assertEqual(result.returncode, 39, result.stderr)
            self.assertIn('PACKAGECONFIG:append:pn-' + slug + ' = " asan"\n', json.loads(log.read_text())['config'])
            invalid = [{'IOTBENCH_BUILD_MODE': 'production'}, {'IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE': '0'},
                       {'IOTBENCH_NATIVE_PATH_ASAN': 'invalid'},
                       {'FIRMWARE': 'router-cwe190-integer-overflow'}]
            invalid += [{flag: '1'} for flag in ('IOTBENCH_ENABLE_REST_FIXTURE', 'IOTBENCH_ENABLE_APACHE_FIXTURE',
                        'IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE', 'IOTBENCH_ENABLE_EMBEDDED_AUTH_FIXTURE',
                        'IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE', 'IOTBENCH_ENABLE_SUDO_ENV_FIXTURE',
                        'IOTBENCH_ENABLE_TELNET_FIXTURE', 'IOTBENCH_ENABLE_FTP_WRITE_FIXTURE')]
            for overrides in invalid:
                log.write_text('not called')
                result = subprocess.run(['bash', str(wrapper)], env=dict(env, **dict(settings, **overrides)),
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(log.read_text(), 'not called')
        # Capture actual QEMU arguments using inert local command stubs. A
        # smart-device fixture must bypass generic MQTT device forwarding too.
        export = sandbox / 'export'
        export.mkdir()
        boot = sandbox / 'boot.sh'
        boot.write_text((ROOT / 'scripts/run-qemu.sh').read_text().replace(
            'DEPLOY_DIR="$(dirname -- "$0")/../deploy-images/${FIRMWARE}/${MACHINE}"',
            'DEPLOY_DIR="' + str(export) + '"'))
        qemu = sandbox / 'qemu-system-aarch64'
        qemu.write_text('#!' + sys.executable + '\nimport json, os, pathlib, sys\n'
                        'pathlib.Path(os.environ["FIXTURE_CALLS"]).write_text(json.dumps(sys.argv[1:]))\n')
        qemu.chmod(0o755)
        zstd = sandbox / 'zstd'
        zstd.write_text('#!/bin/sh\nexit 0\n')
        zstd.chmod(0o755)
        for slug in VARIANTS.values():
            firmware = 'smartplug-' + slug
            (export / ('iotbench-' + firmware + '-qemuarm64.rootfs.ext4.zst')).touch()
            result = subprocess.run(['sh', str(boot)],
                                    env=dict(env, FIRMWARE=firmware, YOCTO_MACHINE='qemuarm64'),
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            args = json.loads(log.read_text())
            self.assertEqual(args[args.index('-nic') + 1], 'none')
            self.assertNotIn('-netdev', args)
            self.assertNotIn('hostfwd', ' '.join(args))
            self.assertNotIn('ip=dhcp', ' '.join(args))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--isolated-fixture', action='store_true', required=True)
    parser.add_argument('--sanitize', action='store_true')
    SANITIZE = parser.parse_args().sanitize
    unittest.main(argv=[__file__], verbosity=2)
