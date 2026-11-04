#!/usr/bin/env python3
"""Run the corrected native path and symlink twins through the same isolated runner as the originals."""

import argparse
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile

os.umask(0o022)
ROOT = Path(__file__).resolve().parents[1]
VULNS = ROOT / 'meta-iotbench/recipes-vulns'


def overlay(module, work, name):
    source = work / name
    shutil.copytree(VULNS / module / 'files', source)
    if module != 'native-path-fixture':
        shared = VULNS / 'native-path-fixture/files'
        for item in ('isolate-path.c',):
            if not (source / item).exists():
                shutil.copyfile(shared / item, source / item)
    shutil.copytree(VULNS / module / 'files-fixed', source, dirs_exist_ok=True)
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--isolated-fixture', action='store_true', required=True)
    parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='native-twins-') as temp:
        work = Path(temp)
        source = overlay('native-path-fixture', work, 'path')
        build = runpy.run_path(str(source / 'fixture-build.py'))
        for cwe in ('022', '020'):
            artifact = build['stage'](work / ('path-' + cwe), cwe, 'fixture', '1')
            info = __import__('json').loads((artifact / 'variant.json').read_text())
            assert info['intentional_vulnerabilities'] == 0 and info['corrected'] is True
            subprocess.run([sys.executable, str(artifact / 'fixture-runner.py'), '--isolated-fixture'],
                           check=True, timeout=300)
            print('PASS corrected native path twin CWE-' + cwe + ': traversal and backup-suffix requests refused')
        source = overlay('cwe061-native-symlink-following', work, 'symlink')
        build = runpy.run_path(str(source / 'fixture-build.py'))
        artifact = build['stage'](work / 'symlink-out', 'fixture', '1')
        info = __import__('json').loads((artifact / 'variant.json').read_text())
        assert info['intentional_vulnerabilities'] == 0 and info['corrected'] is True
        subprocess.run([sys.executable, str(artifact / 'fixture-runner.py'), '--isolated-fixture'],
                       check=True, timeout=300)
        print('PASS corrected native symlink twin CWE-61: pre-established link refused')
    return 0


if __name__ == '__main__':
    sys.exit(main())
