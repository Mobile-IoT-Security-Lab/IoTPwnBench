#!/usr/bin/env python3
"""Offline checks of the corrected embedded-auth twins (files-fixed overlay on files)."""

import argparse
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile

os.environ["LC_ALL"] = "C"
os.umask(0o022)
ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'meta-iotbench/recipes-vulns/cwe798-embedded-auth'
FLAGS = ['-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-fstack-protector-all',
         '-D_FORTIFY_SOURCE=2', '-fPIC', '-shared', '-Wl,-z,relro,-z,now,-z,noexecstack']


def overlay(work):
    source = work / 'overlay'
    shutil.copytree(MODULE / 'files', source)
    shutil.copytree(MODULE / 'files-fixed', source, dirs_exist_ok=True)
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--isolated-fixture', action='store_true')
    parser.add_argument('--rootfs', type=Path)
    parser.add_argument('--variant')
    args = parser.parse_args()
    if not args.isolated_fixture:
        parser.exit(77, 'Tests require --isolated-fixture\n')
    with tempfile.TemporaryDirectory(prefix='auth798-twin-') as temp:
        work = Path(temp)
        source = overlay(work)
        lib = runpy.run_path(str(source / 'fixture-lib.py'))
        verify = runpy.run_path(str(source / 'fixture-verify.py'))['verify']
        if args.rootfs:
            verify(args.rootfs, args.variant, firmware=True)
            print('PASS corrected twin firmware: credential-free artifacts, locked local accounts')
            return 0
        build = runpy.run_path(str(source / 'fixture-build.py'))
        runtime = runpy.run_path(str(source / 'fixture-test.py'))
        inventory = lib['FILES'] and __import__('json').loads((source / 'inventory.json').read_text())
        original = __import__('json').loads((MODULE / 'files/inventory.json').read_text())
        binary = work / 'credential.so'
        subprocess.run(['cc'] + FLAGS + ['-DIOTBENCH_EMBEDDED_AUTH_ENABLED=1',
                        str(source / 'fixtures/c-source/credential.c'), '-o', str(binary)],
                       check=True, timeout=60)
        for machine in lib['MACHINES']:
            try:
                lib['validate_elf'](binary.read_bytes(), machine)
                break
            except ValueError:
                continue
        else:
            raise AssertionError('Host compiler architecture must match a supported QEMU target')
        for variant in lib['VARIANTS']:
            item, old = inventory[variant], original[variant]
            assert item['password'].startswith('RUNTIME_PROVISIONED_') and item['password'] != old['password']
            assert item['username'] == old['username']
            staged = work / variant
            root = build['stage'](staged, 'fixture', '1', machine, variant,
                                  binary if variant == 'c-source' else None)
            verify(staged, variant)
            data = b''.join(p.read_bytes() for p in staged.rglob('*') if p.is_file())
            assert old['password'].encode() not in data, 'Original password still shipped'
            runtime['authenticate'](root, work)
        print('PASS 8 corrected twins: no shipped password, runtime-provisioned secret only, '
              'reference token and unprovisioned service denied')
    return 0


if __name__ == '__main__':
    sys.exit(main())
