#!/usr/bin/env python3
"""Shared host/Yocto installer for one synthetic username/password fixture."""

import argparse
import hashlib
import json
from pathlib import Path
import runpy
import shutil

SOURCE = Path(__file__).resolve().parent
LIB = runpy.run_path(str(SOURCE / 'fixture-lib.py'))


def stage(output, mode, enabled, machine, variant, native_binary=None):
    LIB['validate_build'](mode, enabled, machine, variant)
    output = Path(output).absolute()
    if output.exists():
        raise ValueError('Use a fresh dedicated output tree')
    item = json.loads((SOURCE / 'inventory.json').read_text())[variant]
    source = SOURCE / 'fixtures' / variant / LIB['FILES'][variant]
    if LIB['read_pair'](source, variant) != (item['username'], item['password']):
        raise ValueError('Credential source/inventory drift')
    binary = None
    if variant == 'native':
        if native_binary is None:
            raise ValueError('Native fixture requires the compiled authentication library')
        binary = Path(native_binary).read_bytes()
        LIB['validate_elf'](binary, machine)
        if any(
                value.encode() + b'\0' not in binary for value in (item['username'], item['password'])):
            raise ValueError('Compiled ELF does not contain the intended pair')
    elif native_binary is not None:
        raise ValueError('Native library cannot be mixed into data fixtures')
    root = output / 'usr/share/iotbench/embedded-auth' / variant
    root.mkdir(parents=True)
    shutil.copyfile(source, root / source.name)
    for name in ('fixture-lib.py', 'fixture-service.py', 'fixture-test.py', 'LICENSE'):
        shutil.copyfile(SOURCE / name, root / name)
    if binary is not None:
        (root / 'credential.so').write_bytes(binary)
    (root / 'build-config.json').write_text(json.dumps(dict(
        mode=mode, enabled=enabled, machine=machine, variant=variant), sort_keys=True) + '\n')
    # Fingerprints identify one pair without shipping a second credential store.
    manifest = dict(cwe='CWE-798', active_pairs=1, variant=variant,
                    artifact='credential.so' if binary else source.name,
                    source=source.name, representation=item['representation'],
                    pair_sha256=hashlib.sha256((item['username'] + ':' + item['password']).encode()).hexdigest())
    (root / 'expected.json').write_text(json.dumps(manifest, sort_keys=True) + '\n')
    for path in [output] + list(output.rglob('*')):
        path.chmod(0o755 if path.is_dir() else 0o644)
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--mode', default='production')
    parser.add_argument('--enable', dest='enabled', default='0')
    parser.add_argument('--machine', default='qemuarm64', choices=LIB['MACHINES'])
    parser.add_argument('--variant', required=True, choices=LIB['VARIANTS'])
    parser.add_argument('--native-binary', type=Path)
    try:
        stage(**vars(parser.parse_args()))
    except ValueError as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
