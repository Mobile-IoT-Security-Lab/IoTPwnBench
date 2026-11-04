#!/usr/bin/env python3
"""Test the supplied artifact binaries in a copied, disposable namespace root."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile


def prepare(root, artifact):
    root.mkdir()
    for name in ('oldroot', 'proc', 'run', 'tmp', 'etc'):
        (root / name).mkdir()
    (root / 'etc/passwd').write_text('fixture:x:1000:1000:Synthetic fixture:/tmp:/nonexistent\n')
    (root / 'etc/group').write_text('fixture:x:1000:\n')
    (root / 'etc/nsswitch.conf').write_text('passwd: files\ngroup: files\n')
    shutil.copytree(str(artifact), str(root / 'fixture'))
    copied = set()

    def copy(path, destination=None):
        path = Path(path)
        target = root / (destination or str(path).lstrip('/'))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(path), str(target))
        target.chmod(0o755 if os.access(str(path), os.X_OK) else 0o644)

    def binary(path, destination=None):
        key = (str(path), destination)
        if key in copied:
            return
        copied.add(key)
        if destination != 'already-copied':
            copy(path, destination)
        # Inputs are our compiled fixture and public system runtime binaries.
        # Do not point this runner at untrusted firmware from outside the lab.
        result = subprocess.run(['ldd', str(path)], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, universal_newlines=True, check=True)
        for line in result.stdout.splitlines():
            if 'not found' in line:
                raise RuntimeError('Missing runtime library: ' + line)
            match = re.search(r'(?:=>\s*)?(/[^\s]+)', line)
            if match and (match.group(1), None) not in copied:
                lib = match.group(1)
                copied.add((lib, None))
                copy(lib)

    binary(sys.executable, 'usr/bin/python3')
    stdlib = Path(sysconfig.get_path('stdlib'))
    destination = root / str(stdlib).lstrip('/')
    shutil.copytree(str(stdlib), str(destination), ignore=shutil.ignore_patterns(
        'site-packages', 'dist-packages', '__pycache__', 'test', 'tests', 'ensurepip', 'idlelib', 'tkinter'))
    for extension in destination.rglob('*.so'):
        binary(Path('/') / extension.relative_to(root))
    for name in ('fixture-symlink-cwe061',):
        binary(artifact / 'bin' / name, 'already-copied')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--isolated-fixture', action='store_true', required=True)
    args = parser.parse_args()
    if os.getuid() == 0 or os.geteuid() != os.getuid():
        parser.error('Run as an ordinary unprivileged account, including in a QEMU guest')
    artifact = args.artifact.resolve()
    info = json.loads((artifact / 'variant.json').read_text())
    if (info.get('format') != 1 or info.get('mode') != 'fixture' or info.get('enable') != '1' or
            info.get('cwe') != '061' or info.get('intentional_vulnerabilities') != 0 or info.get('corrected') is not True):
        parser.error('Artifact lacks the explicit single-variant fixture configuration')
    expected = {'fixture-symlink-cwe061', 'isolate-path'}
    if set(info['sha256']) != expected or {p.name for p in (artifact / 'bin').iterdir()} != expected:
        parser.error('Artifact must contain exactly its own variant binaries')
    for name, digest in info['sha256'].items():
        path = artifact / 'bin' / name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            parser.error('Artifact binary hash mismatch: ' + name)
    with tempfile.TemporaryDirectory(prefix='iotbench-symlink-') as temporary:
        base = Path(temporary)
        prepare(base / 'stage', artifact)
        (base / 'root').mkdir()
        subprocess.run([str(artifact / 'bin/isolate-path'), '--isolated-fixture',
                        str(base / 'stage'), str(base / 'root')], check=True, timeout=120)


if __name__ == '__main__':
    main()
