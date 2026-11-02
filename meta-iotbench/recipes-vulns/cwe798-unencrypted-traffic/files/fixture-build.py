#!/usr/bin/env python3
"""Shared Yocto/host staging and fail-closed build policy for the Telnet fixture."""

import argparse
import json
from pathlib import Path

MACHINES = ('qemuarm64', 'qemuarm', 'qemux86-64', 'qemux86', 'qemumips')


def validate_build(mode, enabled, machine):
    if mode != 'fixture' or enabled != '1' or machine not in MACHINES:
        raise ValueError('Telnet requires IOTBENCH_BUILD_MODE=fixture, '
                         'IOTBENCH_ENABLE_TELNET_FIXTURE=1 and a supported QEMU MACHINE')


def stage(output, mode, enabled, machine, target_paths=False, bindir='/usr/bin',
          sysconfdir='/etc', datadir='/usr/share', unitdir='/usr/lib/systemd/system',
          sbindir='/usr/sbin'):
    validate_build(mode, enabled, machine)
    source = Path(__file__).resolve().parent
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    output.chmod(0o755)
    runtime = '' if target_paths else str(output)
    replacements = {'@SBINDIR@': runtime + sbindir}

    def install(name, target, permissions, render=False):
        path = output / target.lstrip('/')
        path.parent.mkdir(parents=True, exist_ok=True)
        parent = path.parent
        while parent != output:
            parent.chmod(0o755)
            parent = parent.parent
        content = (source / name).read_text()
        if render:
            for key, value in replacements.items():
                content = content.replace(key, value)
        path.write_text(content)
        path.chmod(permissions)

    data = datadir + '/iotbench/unencrypted-traffic/'
    install('iotbench-telnet.service', unitdir + '/iotbench-telnet.service', 0o644, True)
    for name in ('NOTICE', 'LICENSE', 'ground-truth.json'):
        install(name, data + name, 0o644)
    manifest = output / (data + 'build-config.json').lstrip('/')
    manifest.write_text(json.dumps({'mode': mode, 'enabled': True, 'machine': machine},
                                   sort_keys=True) + '\n')
    manifest.chmod(0o644)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--mode', default='production')
    parser.add_argument('--enable', default='0')
    parser.add_argument('--machine', default='qemuarm64')
    parser.add_argument('--target-paths', action='store_true')
    for key, default in (('bindir', '/usr/bin'), ('sysconfdir', '/etc'),
                         ('datadir', '/usr/share'), ('unitdir', '/usr/lib/systemd/system'),
                         ('sbindir', '/usr/sbin')):
        parser.add_argument('--' + key, default=default)
    arguments = vars(parser.parse_args())
    arguments['enabled'] = arguments.pop('enable')
    try:
        stage(**arguments)
    except ValueError as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
