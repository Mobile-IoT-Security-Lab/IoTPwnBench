#!/usr/bin/env python3
"""Shared offline native/Yocto builder for the synthetic REST fixture."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess

MACHINES = ('qemuarm64', 'qemuarm', 'qemux86-64', 'qemux86', 'qemumips')
SLUG = 'rest-internal-files'
MANIFEST = 'IOTBENCH_REST_TEST_ONLY_V1\nmode=fixture\nenabled=1\n'
ASSETS = ('api/config.cfg', 'api/status.cfg', 'restricted/marker.txt')


def validate_build(mode, enabled, machine):
    if mode != 'fixture' or enabled != '1' or machine not in MACHINES:
        raise ValueError('Requires IOTBENCH_BUILD_MODE=fixture, '
                         'IOTBENCH_ENABLE_REST_FIXTURE=1 and a supported QEMU MACHINE')


def stage(output, mode='production', enabled='0', machine='qemuarm64',
          binary_dir=None, target_paths=False, cc='cc', datadir='/usr/share'):
    validate_build(mode, enabled, machine)
    if not datadir.startswith('/') or '..' in Path(datadir).parts:
        raise ValueError('datadir must be an absolute target path without traversal')
    if target_paths and binary_dir is None:
        raise ValueError('Target staging requires cross-compiled binaries')
    output = Path(output).absolute()
    # Do not follow a staging path through symlinked ancestors.
    if any(p.is_symlink() for p in (output,) + tuple(output.parents)):
        raise ValueError('Staging path must not contain symlinks')
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a fresh empty staging directory')
    source = Path(__file__).resolve().parent
    root = output / datadir.lstrip('/') / 'iotbench' / SLUG
    runtime = Path(datadir) / 'iotbench' / SLUG if target_paths else root
    if len(str(runtime / 'run/rest.sock').encode()) >= 108:
        raise ValueError('Staging path is too long for a Unix-domain socket')
    root.mkdir(parents=True, mode=0o755)
    root.chmod(0o755)
    for name in ('bin', 'run', 'fs', 'fs/api', 'fs/restricted', 'source'):
        directory = root / name
        directory.mkdir()
        directory.chmod(0o755 if name != 'run' else 0o700)

    def install(name, content, permissions=0o644):
        path = root / name
        path.write_bytes(content)
        path.chmod(permissions)

    install('fs/.fixture-test-only', MANIFEST.encode())
    for name in ASSETS:
        install('fs/' + name, (source / 'assets' / name).read_bytes())
    for name in ('LICENSE', 'NOTICE', 'ground-truth.json'):
        install(name, (source / name).read_bytes())
    for name in ('fixture-rest.c', 'fixture-build.py'):
        install('source/' + name, (source / name).read_bytes())
    for secure in (False, True):
        name = 'fixture-rest-secure' if secure else 'fixture-rest'
        if binary_dir:
            install('bin/' + name, (Path(binary_dir) / name).read_bytes(), 0o755)
        else:
            subprocess.run(shlex.split(cc) + [
                '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                '-fstack-protector-strong', '-D_FORTIFY_SOURCE=2', '-fPIE', '-pie',
                '-Wl,-z,relro,-z,now,-z,noexecstack',
                '-DIOTBENCH_REST_FIXTURE_ENABLED=1',
                '-DREST_SECURE_CONTROL=' + str(int(secure)),
                '-DFIXTURE_BASE=' + json.dumps(str(runtime)),
                str(source / 'fixture-rest.c'), '-o', str(root / 'bin' / name)], check=True)
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', default='production')
    parser.add_argument('--enable', dest='enabled', default='0')
    parser.add_argument('--machine', default='qemuarm64')
    parser.add_argument('--binary-dir', type=Path)
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
