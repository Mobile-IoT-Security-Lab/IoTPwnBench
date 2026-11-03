#!/usr/bin/env python3
"""Offline staging shared by native tests and Yocto do_install."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

MACHINES = ('qemuarm64', 'qemuarm', 'qemux86-64', 'qemux86', 'qemumips')
DEVICES = ('router', 'ipcamera', 'smartplug', 'thermostat', 'plc', 'smartbulb',
           'smarthub', 'envsensor', 'smartspeaker', 'healthmonitor', 'doorlock')
HARDEN = ['-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
          '-D_FORTIFY_SOURCE=2', '-fstack-protector-strong', '-fPIE', '-pie',
          '-Wl,-z,relro,-z,now,-z,noexecstack']


def validate_build(mode, enable, machine):
    if mode != 'fixture' or enable != '1' or machine not in MACHINES:
        raise ValueError('Native path fixtures require mode=fixture, explicit '
                         'IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE=1 and a QEMU machine')


def stage(output, cwe, mode='production', enable='0', machine='qemuarm64',
          binary_dir=None, sanitize=False, cc='cc', datadir='/usr/share'):
    validate_build(mode, enable, machine)
    if cwe not in ('022', '020'):
        raise ValueError('Select one CWE variant: 022 or 020')
    if not datadir.startswith('/') or '..' in Path(datadir).parts:
        raise ValueError('datadir must be an absolute target path without traversal')
    output = Path(output).absolute()
    if any(p.is_symlink() for p in (output,) + tuple(output.parents)):
        raise ValueError('Use an ordinary disposable staging directory')
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a fresh empty staging directory')
    source = Path(__file__).resolve().parent
    root = output / datadir.lstrip('/') / 'iotbench/native-path'
    root.mkdir(parents=True)

    def install(name, content, mode=0o644):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        path.chmod(mode)

    assets = ['allowed/public.cfg']
    if cwe == '022':
        assets += ['sentinel.txt']
    else:
        assets += ['allowed/private.cfg.bak']
    for name in assets:
        install('fs/' + name, (source / 'assets' / name).read_bytes())
    for name in ('LICENSE', 'NOTICE', 'ground-truth.json', 'fixture-runner.py', 'test-session.py'):
        install(name, (source / name).read_bytes())
    for name in ('fixture-path.c', 'isolate-path.c', 'fixture-build.py'):
        install('source/' + name, (source / name).read_bytes())
    service = 'fixture-path-cwe' + cwe
    names = [service, 'isolate-path'] + ([service + '-asan'] if sanitize else [])
    for name in names:
        if binary_dir:
            install('bin/' + name, (Path(binary_dir) / name).read_bytes(), 0o755)
        else:
            path = root / 'bin' / name
            path.parent.mkdir(exist_ok=True)
            flags = [] if name == 'isolate-path' else [
                '-DIOTBENCH_PATH_FIXTURE_ENABLED=1', '-DPATH_FIXTURE_CWE=' + str(int(cwe))]
            if name.endswith('-asan'):
                flags += ['-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                          '-fno-omit-frame-pointer', '-g']
            subprocess.run(shlex.split(cc) + HARDEN + flags +
                           [str(source / ('isolate-path.c' if name == 'isolate-path' else 'fixture-path.c')),
                            '-o', str(path)], check=True)
    info = {'format': 1, 'mode': mode, 'enable': enable, 'cwe': cwe,
            'intentional_vulnerabilities': 0, 'corrected': True, 'sanitized': sanitize,
            # This is a staging target; host-native binaries do not emulate it.
            'machine': machine, 'binary_origin': 'target' if binary_dir else 'host-native',
            'sha256': {name: hashlib.sha256((root / 'bin' / name).read_bytes()).hexdigest()
                       for name in names}}
    install('variant.json', (json.dumps(info, sort_keys=True, indent=2) + '\n').encode())
    for path in root.rglob('*'):
        if path.is_dir():
            path.chmod(0o755)
    root.chmod(0o755)
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cwe', choices=('022', '020'), required=True)
    parser.add_argument('--mode', default='production')
    parser.add_argument('--enable', default='0')
    parser.add_argument('--machine', default='qemuarm64')
    parser.add_argument('--binary-dir', type=Path)
    parser.add_argument('--sanitize', action='store_true')
    parser.add_argument('--cc', default='cc')
    parser.add_argument('--datadir', default='/usr/share')
    try:
        root = stage(**vars(parser.parse_args()))
    except ValueError as error:
        parser.error(str(error))
    print(root)


if __name__ == '__main__':
    main()
