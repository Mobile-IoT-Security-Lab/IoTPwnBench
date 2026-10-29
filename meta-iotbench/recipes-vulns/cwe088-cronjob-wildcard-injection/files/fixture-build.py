#!/usr/bin/env python3
"""Fail-closed native/Yocto staging for the cron wildcard research fixture."""

import argparse
import json
from pathlib import Path
import shlex
import subprocess

MACHINES = ('qemuarm64', 'qemuarm', 'qemux86-64', 'qemux86', 'qemumips')
SLUG = 'cronjob-wildcard-injection'
MANIFEST = 'IOTBENCH_CRON_WILDCARD_TEST_ONLY_V1\nmode=fixture\nenabled=1\n'


def validate_build(mode, enabled, machine):
    if mode != 'fixture' or enabled != '1' or machine not in MACHINES:
        raise ValueError('Requires IOTBENCH_BUILD_MODE=fixture, '
                         'IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE=1 and a supported QEMU MACHINE')


def stage(output, mode='production', enabled='0', machine='qemuarm64',
          binary=None, target_paths=False, cc='cc', datadir='/usr/share'):
    validate_build(mode, enabled, machine)  # Before writes or compilation.
    if not datadir.startswith('/') or '..' in Path(datadir).parts:
        raise ValueError('datadir must be an absolute target path without traversal')
    if target_paths and binary is None:
        raise ValueError('Target staging requires the cross-compiled binary')
    output = Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a fresh empty staging directory')
    source = Path(__file__).resolve().parent
    root = output / datadir.lstrip('/') / 'iotbench' / SLUG
    runtime = Path(datadir) / 'iotbench' / SLUG if target_paths else root
    root.mkdir(parents=True)
    for name in ('bin', 'cron', 'logs', 'source'):
        (root / name).mkdir(mode=0o755)
    (root / 'inbox').mkdir(mode=0o750)

    def install(name, content, permissions=0o644):
        path = root / name
        path.write_bytes(content)
        path.chmod(permissions)
        return path

    install('build-config', MANIFEST.encode())
    helper = root / 'bin/fixture-maintenance'
    if binary:
        install('bin/fixture-maintenance', Path(binary).read_bytes(), 0o755)
    else:
        subprocess.run(shlex.split(cc) + ['-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                       '-DIOTBENCH_CRON_WILDCARD_FIXTURE_ENABLED=1',
                       '-DFIXTURE_ROOT=' + json.dumps(str(runtime)),
                       str(source / 'fixture-maintenance.c'), '-o', str(helper)], check=True)
        helper.chmod(0o755)
    for variant in ('vulnerable', 'secure'):
        config = (source / (variant + '.crontab.in')).read_text()
        config = config.replace('@INBOX@', shlex.quote(str(runtime / 'inbox')))
        config = config.replace('@HELPER@', shlex.quote(str(runtime / 'bin/fixture-maintenance')))
        install('cron/' + variant + '.crontab', config.encode())
    install('inbox/alpha.record', b'synthetic telemetry A\n')
    install('inbox/beta.record', b'synthetic telemetry B\n')
    for name in ('LICENSE', 'NOTICE', 'ground-truth.json', 'fixture-runner.py'):
        install(name, (source / name).read_bytes())
    for name in ('fixture-maintenance.c', 'fixture-build.py',
                 'vulnerable.crontab.in', 'secure.crontab.in'):
        install('source/' + name, (source / name).read_bytes())
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', default='production')
    parser.add_argument('--enable', dest='enabled', default='0')
    parser.add_argument('--machine', default='qemuarm64')
    parser.add_argument('--binary', type=Path)
    parser.add_argument('--target-paths', action='store_true')
    parser.add_argument('--cc', default='cc')
    parser.add_argument('--datadir', default='/usr/share')
    try:
        root = stage(**vars(parser.parse_args()))
    except ValueError as error:
        parser.error(str(error))
    print(root)


if __name__ == '__main__':
    main()
