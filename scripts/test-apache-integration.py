#!/usr/bin/env python3
"""Build-policy and firmware integration checks. No network or BitBake required."""
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / 'meta-iotbench'
FILES = LAYER / 'recipes-vulns/apache-web-fixture/files'
POLICY = runpy.run_path(str(FILES / 'fixture-build.py'))


class Fatal(Exception):
    pass


class BB:
    @staticmethod
    def fatal(message):
        raise Fatal(message)

    class parse:
        @staticmethod
        def mark_dependency(*args):
            pass

        class SkipRecipe(Exception):
            pass


class Data:
    def __init__(self, **variables):
        self.variables = variables

    def getVar(self, name):
        return self.variables.get(name)


def function(path, name):
    pattern = r'^python ' + re.escape(name) + r'\(\) \{\n(.*?)^\}'
    match = re.search(pattern, path.read_text(), re.M | re.S)
    if not match:
        raise AssertionError('Missing recipe function ' + name)
    return compile(textwrap.dedent(match.group(1)), str(path), 'exec')


class Integration(unittest.TestCase):
    def test_matrix_and_single_variant_sources(self):
        recipes = set((LAYER / 'recipes-images').glob('iotbench-*-apache-web.bb'))
        self.assertEqual(len(recipes), 110)
        for device in POLICY['DEVICES']:
            for cwe in POLICY['CWES']:
                path = LAYER / 'recipes-images' / ('iotbench-' + device + '-cwe' + cwe + '-apache-web.bb')
                text = path.read_text()
                self.assertIn('require recipes-devices/' + device + '/device-' + device + '.inc', text)
                self.assertIn('APACHE_FIXTURE_CWE = "' + cwe + '"', text)
                self.assertTrue((FILES / 'variants' / ('cwe' + cwe + '.py')).exists())
                package = LAYER / 'recipes-vulns/apache-web-fixture' / ('apache-web-fixture-cwe' + cwe + '_1.0.bb')
                self.assertIn('APACHE_FIXTURE_CWE = "' + cwe + '"', package.read_text())

    def data(self, mode='fixture', enabled='1'):
        return Data(IOTBENCH_BUILD_MODE=mode, IOTBENCH_ENABLE_APACHE_FIXTURE=enabled,
                    MACHINE='qemuarm64', THISDIR=str(FILES.parent),
                    IOTBENCH_APACHE_LAYER=str(LAYER), APACHE_FIXTURE_CWE='089',
                    IOTBENCH_VULN_INSTALL='apache-web-fixture-cwe089',
                    IMAGE_INSTALL='packagegroup-core-boot apache-web-fixture-cwe089')

    def test_production_and_mixed_image_rejected(self):
        image = function(LAYER / 'recipes-images/iotbench-apache-fixture.inc', 'iotbench_apache_guard')
        package = function(FILES.parent / 'apache-web-fixture.inc', '__anonymous')
        for mode, enabled in (('production', '0'), ('production', '1'), ('fixture', '0')):
            data = self.data(mode, enabled)
            with self.assertRaises(ValueError):
                exec(image, {'d': data, 'bb': BB})
            with self.assertRaises(BB.parse.SkipRecipe):
                exec(package, {'d': data, 'bb': BB})
        data = self.data()
        exec(image, {'d': data, 'bb': BB})
        exec(package, {'d': data, 'bb': BB})
        data.variables['IMAGE_INSTALL'] += ' cwe078-os-command-injection'
        with self.assertRaises(Fatal):
            exec(image, {'d': data, 'bb': BB})
        for machine in ('production-board', '', None):
            with self.assertRaises(ValueError):
                POLICY['validate_build']('fixture', '1', machine)

    def test_rootfs_disables_distribution_service(self):
        metadata = function(LAYER / 'recipes-images/iotbench-apache-fixture.inc', 'iotbench_apache_metadata')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base = root / 'usr/share/iotbench/apache-fixture'
            base.mkdir(parents=True)
            (base / 'scenario.py').touch()
            for name in ('etc/init.d/apache2', 'etc/rc3.d/S91apache2'):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            data = self.data()
            data.variables.update(IMAGE_ROOTFS=str(root), IOTBENCH_DEVICE='router', datadir='/usr/share',
                                  IMAGE_MANIFEST=str(root / 'manifest'))
            (root / 'manifest').write_text('apache-web-fixture-cwe089 qemuarm64 1.0\n')
            exec(metadata, {'d': data, 'bb': BB})
            self.assertFalse((root / 'etc/init.d/apache2').exists())
            self.assertFalse((root / 'etc/rc3.d/S91apache2').exists())
            self.assertEqual(os.readlink(str(root / 'etc/systemd/system/apache2.service')), '/dev/null')
            self.assertIn('Error ', (root / 'etc/apache2/httpd.conf').read_text())
            for name in ('device.conf', 'peripherals.conf'):
                self.assertEqual((root / 'etc/iotbench' / name).read_bytes(),
                                 (LAYER / 'recipes-devices/router/files' / name).read_bytes())
            (root / 'manifest').write_text('apache-web-fixture-cwe089 qemuarm64 1.0\ncwe022-other qemuarm64 1.0\n')
            with self.assertRaises(Fatal):
                exec(metadata, {'d': data, 'bb': BB})

    def test_bulk_build_defaults_exclude_apache(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            docker = root / 'docker'
            docker.write_text('#!/bin/sh\nprintf "%s\\n" "$FIRMWARE" >> "$CAPTURE"\n')
            docker.chmod(0o755)
            capture = root / 'capture'
            env = {k: v for k, v in os.environ.items() if not k.startswith('IOTBENCH_')}
            env.update(PATH=str(root) + ':' + os.environ['PATH'], CAPTURE=str(capture), MACHINES='qemuarm64')
            subprocess.run(['sh', str(ROOT / 'scripts/build-all.sh')], env=env, stdout=subprocess.DEVNULL, check=True)
            self.assertNotIn('apache-web', capture.read_text())
            capture.write_text('')
            env['IOTBENCH_ENABLE_APACHE_FIXTURE'] = '1'
            subprocess.run(['sh', str(ROOT / 'scripts/build-all.sh')], env=env, stdout=subprocess.DEVNULL, check=True)
            self.assertEqual(sum('apache-web' in line for line in capture.read_text().splitlines()), 110)

    def test_qemu_fixture_has_no_network_device(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'scripts').mkdir()
            shutil.copyfile(str(ROOT / 'scripts/run-qemu.sh'), str(root / 'scripts/run-qemu.sh'))
            tools = root / 'tools'
            tools.mkdir()
            zstd = tools / 'zstd'
            zstd.write_text('#!/bin/sh\nfor last; do :; done\n: > "$last"\n')
            zstd.chmod(0o755)
            qemu = tools / 'qemu-system-aarch64'
            qemu.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$CAPTURE"\n')
            qemu.chmod(0o755)
            for firmware in ('router-cwe089-apache-web', 'router-cwe078-os-command-injection'):
                deploy = root / 'deploy-images' / firmware / 'qemuarm64'
                deploy.mkdir(parents=True)
                (deploy / ('iotbench-' + firmware + '-qemuarm64.rootfs.ext4.zst')).touch()
                capture = root / 'capture'
                env = dict(os.environ, PATH=str(tools) + ':' + os.environ['PATH'], FIRMWARE=firmware,
                           YOCTO_MACHINE='qemuarm64', CAPTURE=str(capture), QEMU_PERSIST='0')
                subprocess.run(['sh', str(root / 'scripts/run-qemu.sh')], env=env, check=True, stdout=subprocess.DEVNULL)
                arguments = capture.read_text().splitlines()
                if 'apache-web' in firmware:
                    self.assertNotIn('-netdev', arguments)
                    self.assertFalse(any('hostfwd' in value or 'ip=dhcp' in value for value in arguments))
                    self.assertEqual(arguments[arguments.index('-nic') + 1], 'none')
                else:
                    self.assertIn('-netdev', arguments)
                    self.assertTrue(any('hostfwd=tcp:127.0.0.1:' in value for value in arguments))


if __name__ == '__main__':
    unittest.main(verbosity=2)
