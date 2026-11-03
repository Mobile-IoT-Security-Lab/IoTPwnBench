"""Offline artifact checks; also used on Yocto's completed rootfs. Never executes target ELF."""

import base64
import hashlib
import json
from pathlib import Path
import re
import runpy

SOURCE = Path(__file__).resolve().parent
LIB = runpy.run_path(str(SOURCE / 'fixture-lib.py'))
INVENTORY = json.loads((SOURCE / 'inventory.json').read_text())


def verify(rootfs, variant, firmware=False, production=False):
    rootfs = Path(rootfs)
    if not rootfs.is_dir():
        raise ValueError('An existing extracted rootfs directory is required')
    base = rootfs / 'usr/share/iotbench/embedded-auth'
    if production:
        if base.exists():
            raise ValueError('Fixture artifacts in production rootfs')
    else:
        if sorted(p.name for p in base.iterdir()) != [variant]:
            raise ValueError('Exactly one variant must be installed')
        root = base / variant
        item = INVENTORY[variant]
        config = LIB['json_object']((root / 'build-config.json').read_text())
        LIB['validate_build'](config['mode'], config['enabled'], config['machine'], config['variant'])
        if config['variant'] != variant:
            raise ValueError('Variant/config mismatch')
        native = variant == 'c-source'
        allowed = {item['file'], 'fixture-lib.py', 'fixture-service.py', 'fixture-test.py', 'LICENSE',
                   'build-config.json', 'expected.json'} | ({'credential.so'} if native else set())
        if {p.name for p in root.iterdir()} != allowed:
            raise ValueError('Extra/missing fixture artifacts')
        for path in [root] + list(root.iterdir()):
            if path.is_symlink() or path.stat().st_mode & 0o7777 != (0o755 if path.is_dir() else 0o644):
                raise ValueError('Unexpected artifact permissions/type')
        expected_pair = (item['username'], item['password'])
        if LIB['read_pair'](root / item['file'], variant) != expected_pair:
            raise ValueError('Expected one matching artifact pair')
        expected = dict(cwe='CWE-798', active_pairs=1, variant=variant,
                        artifact='credential.so' if native else item['file'], source=item['file'],
                        representation=item['representation'],
                        pair_sha256=hashlib.sha256(':'.join(expected_pair).encode()).hexdigest())
        if json.loads((root / 'expected.json').read_text()) != expected:
            raise ValueError('Finding manifest mismatch')
        if native:
            binary = (root / 'credential.so').read_bytes()
            LIB['validate_elf'](binary, config['machine'])
            if any(binary.count(v.encode() + b'\0') != 1 for v in expected_pair):
                raise ValueError('Missing expected credential in compiled ELF')
    # Inspect the whole extracted filesystem, including binaries. All occurrences
    # must belong to the selected pair and its declared source/active artifact.
    for path in rootfs.rglob('*'):
        if path.is_symlink() or not path.is_file():
            continue
        data = path.read_bytes()
        occurrences = set(re.findall(rb'(?:fixture798_[A-Za-z0-9_]+|SYNTH_ONLY_798_[A-Za-z0-9_]+_P9!)', data))
        for other_variant, item in INVENTORY.items():
            values = (item['username'].encode(), item['password'].encode())
            encoded = base64.b64encode(b':'.join(values))
            if any(v in data for v in values) or encoded in data:
                if production or other_variant != variant or path.name not in (item['file'], 'credential.so') or path.parent != base / variant:
                    raise ValueError('Credential copy outside the selected artifact: ' + str(path))
                occurrences.difference_update(values)
        if occurrences:
            raise ValueError('Unlisted synthetic credential in artifact: ' + str(path))
    if firmware and not production:
        shadow = (rootfs / 'etc/shadow').read_text().splitlines()
        if not shadow or any(line.split(':')[1] not in ('!', '*', '!!', '!*') for line in shadow):
            raise ValueError('Fixture firmware must have locked local password accounts')
    return True
