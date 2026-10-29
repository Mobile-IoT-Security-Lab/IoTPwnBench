#!/usr/bin/env python3
"""Shared offline/Yocto staging. Fail closed before creating output."""

import argparse
import hashlib
import json
from pathlib import Path
import runpy
import shutil

SOURCE = Path(__file__).resolve().parent
LIB = runpy.run_path(str(SOURCE / 'fixture-lib.py'))


def stage(output, mode, enabled, machine, variant, datadir='/usr/share'):
    LIB['validate_build'](mode, enabled, machine, variant)
    output = Path(output).absolute()
    if output.exists():
        raise ValueError('Use a new, dedicated fixture output directory')
    if not datadir.startswith('/') or '..' in Path(datadir).parts:
        raise ValueError('datadir must be an absolute target path')
    inventory = json.loads((SOURCE / 'synthetic-inventory.json').read_text())
    expected = json.loads((SOURCE / 'expected-findings.json').read_text())[variant]
    item = inventory[variant]
    fixture = SOURCE / 'fixtures' / variant
    content = (fixture / item['file']).read_bytes()
    # Source drift is rejected before writing any firmware files.
    stored = LIB['credential'](content.decode(), item['parser'], item['field'])
    if LIB['decode'](stored, item['encoding']) != item['value']:
        raise ValueError('Source credential differs from the synthetic inventory')
    if hashlib.sha256(item['value'].encode()).hexdigest() != expected['sha256']:
        raise ValueError('Expected finding differs from synthetic inventory')
    finding = dict(path=item['file'], line=expected['line'], field=expected['field'],
                   value=item['value'], encoding=item['encoding'])
    if LIB['scan'](fixture) != [finding]:
        raise ValueError('Source must contain exactly the manifest credential at its declared location')
    if (not LIB['SECRET'].fullmatch(item['value'])
            or expected['fixture'] != variant or expected['cwe'] != 'CWE-798'
            or expected['scenario_count'] != 1
            or expected['location'] != item['field']
            or expected['encoding'] != item['encoding']
            or expected['usage'] != 'local-simulated-authentication'):
        raise ValueError('Manifest must describe one synthetic CWE-798 authentication scenario')
    if LIB['scan'](SOURCE / 'negative'):
        raise ValueError('Negative controls must not contain credential findings')
    root = output / datadir.lstrip('/') / 'iotbench/password-leak' / variant
    root.mkdir(parents=True, mode=0o755)
    root.chmod(0o755)
    for parent in root.parents:
        if parent == output.parent:
            break
        parent.chmod(0o755)
    for name in (item['file'],):
        shutil.copyfile(fixture / name, root / name)
    for name in ('fixture-auth.py', 'fixture-lib.py', 'LICENSE', 'NOTICE'):
        shutil.copyfile(SOURCE / name, root / name)
    shutil.copytree(SOURCE / 'negative', root / 'negative')
    policy = {key: item[key] for key in ('parser', 'field', 'encoding')}
    policy.update(source=item['file'], usage='local-simulated-authentication',
                  native_reference=item.get('native_reference'))
    (root / 'authentication.json').write_text(json.dumps(policy, indent=2) + '\n')
    (root / 'build-config.json').write_text(json.dumps(dict(
        mode=mode, enabled=enabled, machine=machine, variant=variant), sort_keys=True) + '\n')
    # Only this variant's metadata is shipped; never install the secret inventory
    # or manifests for other variants as additional credential exposure artifacts.
    expected = dict(expected, path=(datadir.lstrip('/') + '/iotbench/password-leak/'
                                   + variant + '/' + item['file']))
    (root / 'expected-findings.json').write_text(json.dumps([expected], indent=2) + '\n')
    for path in root.rglob('*'):
        path.chmod(0o755 if path.is_dir() else 0o644)
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--variant', required=True, choices=LIB['VARIANTS'])
    parser.add_argument('--mode', default='production')
    parser.add_argument('--enable', dest='enabled', default='0')
    parser.add_argument('--machine', default='qemuarm64')
    parser.add_argument('--datadir', default='/usr/share')
    try:
        stage(**vars(parser.parse_args()))
    except ValueError as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
