#!/usr/bin/env python3
"""Offline native staging and Yocto do_install for the opt-in CWE-61 fixture."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

MACHINES = ('qemuarm64', 'qemuarm', 'qemux86-64', 'qemux86', 'qemumips')
DEVICES = ('router', 'ipcamera', 'smartplug', 'thermostat', 'plc', 'smartbulb',
           'smarthub', 'envsensor', 'smartspeaker', 'healthmonitor', 'doorlock')
HARDEN = ['-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-D_FORTIFY_SOURCE=2',
          '-fstack-protector-strong', '-fPIE', '-pie', '-Wl,-z,relro,-z,now,-z,noexecstack']
PACKAGE = 'cwe061-native-symlink-following'


def validate_build(mode, enable, machine):
    if mode != 'fixture' or enable != '1' or machine not in MACHINES:
        raise ValueError('Native symlink fixtures require mode=fixture, explicit '
                         'IOTBENCH_ENABLE_NATIVE_SYMLINK_FIXTURE=1 and a QEMU machine')


def stage(output, mode='production', enable='0', machine='qemuarm64',
          binary_dir=None, cc='cc', datadir='/usr/share'):
    validate_build(mode, enable, machine)
    if not datadir.startswith('/') or '..' in Path(datadir).parts:
        raise ValueError('datadir must be an absolute target path without traversal')
    output = Path(output).absolute()
    if any(p.is_symlink() for p in (output,) + tuple(output.parents)):
        raise ValueError('Use an ordinary disposable staging directory')
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a fresh empty staging directory')
    source = Path(__file__).resolve().parent
    shared = source if (source / 'isolate-path.c').is_file() else source.parents[1] / 'native-path-fixture/files'
    root = output / datadir.lstrip('/') / 'iotbench/native-symlink'
    root.mkdir(parents=True)

    def install(name, content, permissions=0o644):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        path.chmod(permissions)

    for name in ('allowed/public.cfg', 'sentinel.txt'):
        install('fs/' + name, (source / 'assets' / name).read_bytes())
    for name in ('LICENSE', 'NOTICE', 'ground-truth.json', 'fixture-runner.py', 'test-session.py'):
        install(name, (source / name).read_bytes())
    for name in ('fixture-symlink.c', 'fixture-build.py'):
        install('source/' + name, (source / name).read_bytes())
    install('source/isolate-path.c', (shared / 'isolate-path.c').read_bytes())
    names = ('fixture-symlink-cwe061', 'isolate-path')
    for name in names:
        if binary_dir:
            install('bin/' + name, (Path(binary_dir) / name).read_bytes(), 0o755)
        else:
            path = root / 'bin' / name
            path.parent.mkdir(exist_ok=True)
            flags = [] if name == 'isolate-path' else ['-DIOTBENCH_SYMLINK_FIXTURE_ENABLED=1']
            src = shared / 'isolate-path.c' if name == 'isolate-path' else source / 'fixture-symlink.c'
            subprocess.run(shlex.split(cc) + HARDEN + flags + [str(src), '-o', str(path)], check=True)
    info = {'format': 1, 'mode': mode, 'enable': enable, 'cwe': '061',
            'intentional_vulnerabilities': 1, 'machine': machine,
            'binary_origin': 'target' if binary_dir else 'host-native',
            'sha256': {name: hashlib.sha256((root / 'bin' / name).read_bytes()).hexdigest()
                       for name in names}}
    install('variant.json', (json.dumps(info, sort_keys=True, indent=2) + '\n').encode())
    for path in [root] + list(root.rglob('*')):
        if path.is_dir():
            path.chmod(0o755)
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', default='production')
    parser.add_argument('--enable', default='0')
    parser.add_argument('--machine', default='qemuarm64')
    parser.add_argument('--binary-dir', type=Path)
    parser.add_argument('--cc', default='cc')
    parser.add_argument('--datadir', default='/usr/share')
    try:
        root = stage(**vars(parser.parse_args()))
    except ValueError as error:
        parser.error(str(error))
    print(root)


if __name__ == '__main__':
    main()
