#!/usr/bin/env python3
"""Offline build integration and isolated end-to-end socket tests for CWE-61."""
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
RECIPE = LAYER / 'recipes-vulns/cwe061-native-symlink-following'
FILES = RECIPE / 'files'
BUILD = runpy.run_path(str(FILES / 'fixture-build.py'))
PACKAGE = BUILD['PACKAGE']
IMAGE = LAYER / 'recipes-images/iotbench-native-symlink-fixture.inc'


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
    def __init__(self, mode='fixture', enable='1', machine='qemuarm64'):
        self.values = {'IOTBENCH_BUILD_MODE': mode, 'IOTBENCH_ENABLE_NATIVE_SYMLINK_FIXTURE': enable,
                       'MACHINE': machine, 'THISDIR': str(RECIPE), 'IOTBENCH_SYMLINK_LAYER': str(LAYER),
                       'IOTBENCH_VULN_INSTALL': PACKAGE, 'IMAGE_INSTALL': 'packagegroup-core-boot ' + PACKAGE}

    def getVar(self, key):
        return self.values.get(key)


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='native-symlink-tests-')
        cls.base = Path(cls.temporary.name)
        cls.artifact = BUILD['stage'](cls.base / 'native', 'fixture', '1')

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_artifact_through_isolated_unix_socket(self):
        subprocess.run([sys.executable, str(self.artifact / 'fixture-runner.py'),
                        '--isolated-fixture'], check=True, timeout=120)

    def test_production_exclusion_and_guards(self):
        package_guard = function(RECIPE / (PACKAGE + '_1.0.bb'), '__anonymous')
        image_guard = function(IMAGE, 'iotbench_native_symlink_guard')
        for mode in ('fixture', 'production', None):
            for enable in ('1', '0', None):
                for machine in BUILD['MACHINES'] + ('production-board', None):
                    valid = mode == 'fixture' and enable == '1' and machine in BUILD['MACHINES']
                    for code in (package_guard, image_guard):
                        data = Data(mode, enable, machine)
                        if valid:
                            exec(code, {'d': data, 'bb': BB})
                        else:
                            with self.assertRaises(ValueError):
                                exec(code, {'d': data, 'bb': BB})
                    if not valid:
                        output = self.base / 'excluded'
                        with self.assertRaises(ValueError):
                            BUILD['stage'](output, mode, enable, machine)
                        self.assertFalse(output.exists())
        for key in ('IOTBENCH_VULN_INSTALL', 'IMAGE_INSTALL'):
            data = Data()
            data.values[key] += ' cwe-other'
            with self.assertRaises(ValueError):
                exec(image_guard, {'d': data, 'bb': BB})
        for flags in ([], ['-DIOTBENCH_SYMLINK_FIXTURE_ENABLED=0']):
            output = self.base / 'production-stub'
            subprocess.run(['cc'] + BUILD['HARDEN'] + flags +
                           [str(FILES / 'fixture-symlink.c'), '-o', str(output)], check=True)
            result = subprocess.run([str(output), '--isolated-fixture'], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=5)
            self.assertEqual(result.returncode, 77)
            self.assertNotIn(b'public.cfg', output.read_bytes())
        result = subprocess.run([str(self.artifact / 'bin/fixture-symlink-cwe061'), '--isolated-fixture'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        self.assertEqual(result.returncode, 77, 'Enabled binary must refuse the host root')

    def test_all_device_recipes_and_target_staging(self):
        devices = {p.name for p in (LAYER / 'recipes-devices').iterdir() if p.is_dir()}
        self.assertEqual(devices, set(BUILD['DEVICES']))
        for device in devices:
            content = (LAYER / 'recipes-images' / ('iotbench-' + device + '-' + PACKAGE + '.bb')).read_text()
            for required in ('recipes-images/iotbench-image.inc',
                             'recipes-devices/{0}/device-{0}.inc'.format(device),
                             'recipes-images/iotbench-native-symlink-fixture.inc'):
                self.assertIn('require ' + required, content)
        # Emulate actual SRC_URI unpacking, including the shared namespace C source.
        unpack = self.base / 'unpack'
        unpack.mkdir()
        recipe = (RECIPE / (PACKAGE + '_1.0.bb')).read_text()
        uri = re.search(r'SRC_URI = "(.*?)"', recipe, re.S).group(1)
        for item in uri.replace('\\\n', ' ').split():
            self.assertTrue(item.startswith('file://'))
            name = item[7:]
            source = FILES / name
            if not source.exists():
                source = LAYER / 'recipes-vulns/native-path-fixture/files' / name
            if source.is_dir():
                shutil.copytree(str(source), str(unpack / name))
            else:
                shutil.copyfile(str(source), str(unpack / name))
        stage = runpy.run_path(str(unpack / 'fixture-build.py'))['stage']
        for machine in BUILD['MACHINES']:
            output = stage(self.base / machine, 'fixture', '1', machine, binary_dir=self.artifact / 'bin')
            info = json.loads((output / 'variant.json').read_text())
            self.assertEqual(info['binary_origin'], 'target')
            for name, digest in info['sha256'].items():
                self.assertEqual((output / 'bin' / name).read_bytes(), (self.artifact / 'bin' / name).read_bytes())
                self.assertEqual(hashlib.sha256((output / 'bin' / name).read_bytes()).hexdigest(), digest)
            self.assertEqual({str(p.relative_to(output / 'fs')) for p in (output / 'fs').rglob('*') if p.is_file()},
                             {'allowed/public.cfg', 'sentinel.txt'})
            for path in [output] + list(output.rglob('*')):
                self.assertFalse(path.is_symlink())
                expected = 0o755 if path.is_dir() or path.parent == output / 'bin' else 0o644
                self.assertEqual(path.stat().st_mode & 0o7777, expected)
        self.assertNotIn('SECURITY_CFLAGS =', recipe)
        self.assertNotIn('-fno-stack-protector', recipe)
        self.assertNotIn('INITSCRIPT', recipe)
        kernel = (LAYER / 'recipes-kernel/linux/linux-yocto_%.bbappend').read_text()
        expression = next(line for line in kernel.splitlines() if 'file://native-path-fixture.cfg' in line)
        expression = expression.split('${@', 1)[1].rsplit('}', 1)[0]
        for mode, enable, selected in (('fixture', '1', True), ('fixture', '0', False),
                                       ('production', '1', False), ('production', '0', False)):
            self.assertEqual(bool(eval(expression, {'d': Data(mode, enable)})), selected)

    def test_compiler_protections(self):
        truth = json.loads((FILES / 'ground-truth.json').read_text())
        self.assertEqual((truth['primary_cwe'], truth['broader_cwe'], truth['intentional_vulnerabilities']),
                         ('CWE-61', 'CWE-59', 1))
        for binary in (self.artifact / 'bin').iterdir():
            header = subprocess.check_output(['readelf', '-h', str(binary)]).decode()
            self.assertRegex(header, r'Type:\s+DYN')
            program = subprocess.check_output(['readelf', '-W', '-l', str(binary)]).decode()
            self.assertIn('GNU_RELRO', program)
            self.assertNotIn('RWE', next(line for line in program.splitlines() if 'GNU_STACK' in line))
            dynamic = subprocess.check_output(['readelf', '-d', str(binary)]).decode()
            self.assertIn('BIND_NOW', dynamic)
            symbols = subprocess.check_output(['readelf', '-Ws', str(binary)]).decode()
            self.assertIn('__stack_chk_fail', symbols)

    def test_rootfs_metadata_and_integrity(self):
        driver = self.base / 'metadata.py'
        driver.write_text('import json, re, sys, textwrap\nfrom pathlib import Path\n'
                          'class Data:\n    def getVar(self, key): return values.get(key)\n'
                          'class BB:\n    @staticmethod\n    def fatal(message): raise ValueError(message)\n'
                          'values = json.loads(sys.argv[2])\n'
                          'source = re.search(r"^python iotbench_native_symlink_metadata\\(\\) \\{\\n(.*?)^\\}", '
                          'Path(sys.argv[1]).read_text(), re.M | re.S).group(1)\n'
                          'exec(compile(textwrap.dedent(source), sys.argv[1], "exec"), {"d": Data(), "bb": BB})\n')
        rootfs = self.base / 'rootfs'
        output = BUILD['stage'](rootfs, 'fixture', '1', binary_dir=self.artifact / 'bin')
        manifest = rootfs / 'image.manifest'
        manifest.write_text(PACKAGE + ' qemuarm64 1.0\n')
        data = Data()
        data.values.update(IMAGE_ROOTFS=str(rootfs), IMAGE_MANIFEST=str(manifest), datadir='/usr/share')

        def check(success=True):
            # Namespace root models Yocto pseudo's ownership for metadata only.
            result = subprocess.run(['unshare', '--user', '--map-root-user', sys.executable,
                                     str(driver), str(IMAGE), json.dumps(data.values)],
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
                self.assertEqual((rootfs / 'etc/iotbench' / name).read_bytes(),
                                 (LAYER / 'recipes-devices' / device / 'files' / name).read_bytes())
        binary = output / 'bin/fixture-symlink-cwe061'
        original = binary.read_bytes()
        binary.write_bytes(original + b'tampered')
        check(False)
        binary.write_bytes(original)
        entry = output / 'fs/allowed/public.cfg'
        original = entry.read_bytes()
        entry.unlink()
        entry.symlink_to('../sentinel.txt')
        check(False)
        entry.unlink()
        entry.write_bytes(original)
        entry.chmod(0o666)
        check(False)
        entry.chmod(0o644)
        manifest.write_text(PACKAGE + ' qemuarm64 1.0\ncwe-other qemuarm64 1.0\n')
        check(False)

    def test_catalog_wrapper_and_network_exclusion(self):
        sandbox = self.base / 'wrappers'
        sandbox.mkdir()
        log = sandbox / 'calls'
        docker = sandbox / 'docker'
        docker.write_text('#!/bin/sh\nprintf "%s|%s\\n" "$FIRMWARE" "$*" >> "$FIXTURE_CALLS"\n')
        docker.chmod(0o755)
        env = {k: v for k, v in os.environ.items() if not k.startswith('IOTBENCH_')}
        env.update(PATH=str(sandbox) + ':' + os.environ['PATH'], FIXTURE_CALLS=str(log), MACHINES='qemuarm64')
        for extra, count in (({}, 0), ({'IOTBENCH_ENABLE_NATIVE_SYMLINK_FIXTURE': '1'}, 11)):
            log.write_text('')
            subprocess.run(['sh', str(ROOT / 'scripts/build-all.sh')], env=dict(env, **extra),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=30)
            calls = [line for line in log.read_text().splitlines() if PACKAGE in line]
            self.assertEqual(len(calls), count)
            self.assertTrue(all('-e IOTBENCH_ENABLE_NATIVE_SYMLINK_FIXTURE=1' in line and
                                '-e IOTBENCH_BUILD_MODE=fixture' in line for line in calls))
        bootstrap = sandbox / 'bootstrap.sh'
        bootstrap.write_text(':\n')
        wrapper = sandbox / 'build.sh'
        wrapper.write_text((ROOT / 'scripts/container-build-and-export.sh').read_text().replace(
            'source /opt/yocto/yocto-env.sh', 'source ' + str(bootstrap)))
        bitbake = sandbox / 'bitbake'
        bitbake.write_text('#!' + sys.executable + '\nimport json, os, pathlib, sys\n'
                           'args = sys.argv[1:]\nconf = pathlib.Path(args[1]) if args[0] == "-r" else None\n'
                           'pathlib.Path(os.environ["FIXTURE_CALLS"]).write_text(json.dumps('
                           '{"args": args, "config": conf.read_text() if conf else None}))\nsys.exit(39)\n')
        bitbake.chmod(0o755)
        settings = {'FIRMWARE': 'router-' + PACKAGE, 'IOTBENCH_ENABLE_NATIVE_SYMLINK_FIXTURE': '1'}
        result = subprocess.run(['bash', str(wrapper)], env=dict(env, **settings),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        self.assertEqual(result.returncode, 39, result.stderr)
        call = json.loads(log.read_text())
        self.assertEqual(call['config'], 'IOTBENCH_BUILD_MODE = "fixture"\nIOTBENCH_ENABLE_NATIVE_SYMLINK_FIXTURE = "1"\n')
        self.assertFalse(Path(call['args'][1]).exists())
        invalid = [{'IOTBENCH_BUILD_MODE': 'production'}, {'IOTBENCH_ENABLE_NATIVE_SYMLINK_FIXTURE': '0'},
                   {'FIRMWARE': 'router-cwe190-integer-overflow'}]
        invalid += [{flag: '1'} for flag in set(re.findall(r'IOTBENCH_ENABLE_[A-Z_]+_FIXTURE',
                    (ROOT / 'scripts/container-build-and-export.sh').read_text()))
                    if flag != 'IOTBENCH_ENABLE_NATIVE_SYMLINK_FIXTURE']
        for overrides in invalid:
            log.write_text('not called')
            result = subprocess.run(['bash', str(wrapper)], env=dict(env, **dict(settings, **overrides)),
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(log.read_text(), 'not called')
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
        for device in BUILD['DEVICES']:
            firmware = device + '-' + PACKAGE
            (export / ('iotbench-' + firmware + '-qemuarm64.rootfs.ext4.zst')).touch()
            result = subprocess.run(['sh', str(boot)], env=dict(env, FIRMWARE=firmware, YOCTO_MACHINE='qemuarm64'),
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
    parser.parse_args()
    unittest.main(argv=[__file__], verbosity=2)
