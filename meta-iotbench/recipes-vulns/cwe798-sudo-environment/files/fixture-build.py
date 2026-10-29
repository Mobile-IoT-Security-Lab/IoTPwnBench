#!/usr/bin/env python3
"""Shared fail-closed build policy and staging for the synthetic sudo fixture."""

import argparse
from pathlib import Path
import shlex
import subprocess

MACHINES = ('qemuarm64', 'qemuarm', 'qemux86-64', 'qemux86', 'qemumips')
MANIFEST = 'IOTBENCH_SUDO_ENV_TEST_ONLY_V1\nmode=fixture\nenabled=1\n'
SLUG = 'sudo-environment'


def validate_build(mode, enabled, machine):
    if mode != 'fixture' or enabled != '1' or machine not in MACHINES:
        raise ValueError('Sudo environment fixture requires IOTBENCH_BUILD_MODE=fixture, '
                         'IOTBENCH_ENABLE_SUDO_ENV_FIXTURE=1 and a supported QEMU MACHINE')


def stage(output, mode='production', enabled='0', machine='qemuarm64',
          binary=None, target_paths=False, cc='cc', bindir='/usr/bin',
          base_bindir='/bin', sysconfdir='/etc', datadir='/usr/share'):
    validate_build(mode, enabled, machine)  # Must precede any output or compile.
    source = Path(__file__).resolve().parent
    output = Path(output).resolve()
    if not target_paths and output.exists() and any(output.iterdir()):
        raise ValueError('Use a fresh empty staging directory')
    output.mkdir(parents=True, exist_ok=True)
    output.chmod(0o755)
    data = datadir + '/iotbench/' + SLUG
    runtime = '' if target_paths else str(output)

    def install(target, content, mode):
        path = output / target.lstrip('/')
        path.parent.mkdir(parents=True, exist_ok=True)
        parent = path.parent
        while parent != output:
            parent.chmod(0o755)
            parent = parent.parent
        path.write_bytes(content)
        path.chmod(mode)
        return path

    install(data + '/build-config', MANIFEST.encode(), 0o644)
    helper = install(bindir + '/fixture-sudo-env', b'', 0o755)
    if binary:
        helper.write_bytes(Path(binary).read_bytes())
    else:
        subprocess.run(shlex.split(cc) + ['-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                       '-DIOTBENCH_SUDO_ENV_FIXTURE_ENABLED=1',
                       '-DFIXTURE_MANIFEST="' + runtime + data + '/build-config"',
                       str(source / 'fixture-sudo-env.c'), '-o', str(helper)], check=True)
    policy = (source / 'iotbench-sudo-environment').read_text()
    policy = policy.replace('@BINDIR@', runtime + bindir).replace('@BASE_BINDIR@', base_bindir)
    install(sysconfdir + '/sudoers.d/iotbench-sudo-environment', policy.encode(), 0o440)
    for name in ('LICENSE', 'NOTICE', 'ground-truth.json', 'fixture-sudo-env.c',
                 'fixture-build.py', 'test-session.py'):
        content = (source / name).read_text()
        if name == 'test-session.py':
            for key, value in (('@BINDIR@', runtime + bindir), ('@DATADIR@', runtime + datadir),
                               ('@SYSCONFDIR@', runtime + sysconfdir)):
                content = content.replace(key, value)
        install(data + '/' + name, content.encode(), 0o644)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--mode', default='production')
    parser.add_argument('--enable', dest='enabled', default='0')
    parser.add_argument('--machine', default='qemuarm64')
    parser.add_argument('--binary', type=Path)
    parser.add_argument('--target-paths', action='store_true')
    parser.add_argument('--cc', default='cc')
    for key, default in (('bindir', '/usr/bin'), ('base-bindir', '/bin'),
                         ('sysconfdir', '/etc'), ('datadir', '/usr/share')):
        parser.add_argument('--' + key, default=default)
    try:
        stage(**vars(parser.parse_args()))
    except ValueError as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
