#!/usr/bin/env python3
"""Execute the actual synthetic sudo policy in a disposable, networkless x86 VM.

Requires an x86_64 Linux host, QEMU, a readable matching Linux kernel with
initramfs support, and Debian-style /usr/bin/python3, BusyBox, sudo and PAM.
Copies only binaries/libraries and generated synthetic accounts/configuration;
never copies host credentials, installs packages or changes host sudo policy.
"""

import argparse
import gzip
import os
from pathlib import Path
import re
import runpy
import shutil
import stat
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'meta-iotbench/recipes-vulns/cwe798-sudo-environment/files'
BUILD = runpy.run_path(str(SOURCE / 'fixture-build.py'))


def initramfs(root, destination):
    """Write reproducible root-owned newc metadata without needing host root."""
    with destination.open('wb') as output:
        with gzip.GzipFile(fileobj=output, mode='wb', mtime=0, filename='') as archive:
            counter = 0

            def entry(name, mode, data=b'', major=0, minor=0):
                nonlocal counter
                counter += 1
                encoded = name.encode() + b'\0'
                fields = [counter, mode, 0, 0, 1, 0, len(data), 0, 0,
                          major, minor, len(encoded), 0]
                header = b'070701' + ''.join('{:08x}'.format(value) for value in fields).encode()
                archive.write(header + encoded + b'\0' * (-(len(header) + len(encoded)) % 4))
                archive.write(data + b'\0' * (-len(data) % 4))

            for path in sorted(root.rglob('*')):
                name = str(path.relative_to(root))
                metadata = path.lstat()
                if path.is_symlink():
                    data = os.readlink(str(path)).encode()
                elif path.is_file():
                    data = path.read_bytes()
                else:
                    data = b''
                entry(name, metadata.st_mode, data)
            entry('dev/console', stat.S_IFCHR | 0o600, major=5, minor=1)
            entry('dev/null', stat.S_IFCHR | 0o666, major=1, minor=3)
            entry('TRAILER!!!', 0)


def populate(root):
    BUILD['stage'](root, 'fixture', '1', 'qemux86-64', target_paths=True)
    copied = set()

    def binary(path, target=None):
        path = Path(path)
        target = Path(target) if target else path
        if str(target) in copied:
            return
        copied.add(str(target))
        destination = root / str(target).lstrip('/')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(path), str(destination))  # Dereference trusted host links.
        destination.chmod(stat.S_IMODE(path.stat().st_mode))
        result = subprocess.run(['ldd', str(path)], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, universal_newlines=True, timeout=10)
        if 'not found' in result.stdout:
            raise RuntimeError('Missing binary dependency: ' + result.stdout)
        for dependency in re.findall(r'(?<!\S)(/[^\s]+)', result.stdout):
            binary(dependency)

    binary('/usr/bin/python3')
    binary('/usr/bin/sudo')
    binary('/usr/sbin/visudo')
    binary('/usr/bin/busybox', '/bin/busybox')
    # Plugins and dlopened modules do not appear in the executable's ldd output.
    plugin_dirs = [path for path in (Path('/usr/lib/sudo'), Path('/usr/libexec/sudo')) if path.is_dir()]
    if not plugin_dirs:
        raise RuntimeError('A Debian-style sudo plugin directory is required')
    for directory in plugin_dirs:
        for path in directory.iterdir():
            if path.is_file() and ('.so' in path.name or path.name == 'sesh'):
                binary(path)
    library_dirs = (Path('/lib/x86_64-linux-gnu'), Path('/usr/lib/x86_64-linux-gnu'))
    for pattern in ('security/pam_permit.so', 'security/pam_deny.so', 'libnss_files.so.2'):
        candidates = [path for directory in library_dirs for path in directory.glob(pattern)]
        if not candidates:
            raise RuntimeError('Missing runtime module: ' + pattern)
        binary(candidates[0])
    stdlib = Path(subprocess.check_output(
        ['/usr/bin/python3', '-c', 'import sysconfig; print(sysconfig.get_path("stdlib"))'],
        universal_newlines=True).strip())
    if not str(stdlib).startswith('/usr/lib/python3.'):
        raise RuntimeError('Use a Debian-style system Python installation')
    shutil.copytree(str(stdlib), str(root / str(stdlib).lstrip('/')),
                    ignore=shutil.ignore_patterns('__pycache__', 'test', 'tests', 'dist-packages'))
    for module in stdlib.glob('lib-dynload/*.so'):
        binary(module)
    for directory in ('dev', 'proc', 'run', 'var/log', 'var/lib/sudo', 'tmp', 'etc/pam.d'):
        (root / directory).mkdir(parents=True, exist_ok=True)
    (root / 'tmp').chmod(0o1777)
    (root / 'usr/bin/sudo').chmod(0o4755)
    for applet in ('sh', 'mount', 'poweroff', 'cat'):
        (root / 'bin' / applet).symlink_to('busybox')
    synthetic_files = {
        'etc/passwd': 'root:x:0:0:synthetic:/nonexistent:/bin/false\n'
                      'fixtureenv:x:989:989:synthetic:/nonexistent:/bin/false\n',
        'etc/group': 'root:x:0:\nfixtureenv:x:989:\n',
        'etc/shadow': 'root:!:1:0:99999:7:::\nfixtureenv:!:1:0:99999:7:::\n',
        'etc/nsswitch.conf': 'passwd: files\ngroup: files\nshadow: files\nhosts: files\n',
        'etc/hosts': '127.0.0.1 localhost\n',
        'etc/sudo.conf': '# Test VM: upstream default sudoers plugins only\n',
        'etc/sudoers': '# Disposable fixture VM: only the scoped rule is granted.\n'
                       'Defaults !use_pty\n@includedir /etc/sudoers.d\n',
        # Authentication is unavailable; the exact helper uses NOPASSWD.
        'etc/pam.d/sudo': 'auth required pam_deny.so\naccount required pam_permit.so\n'
                         'session required pam_permit.so\n',
        'init': '#!/bin/sh\n/bin/mount -t proc proc /proc\n/bin/mount -t devtmpfs devtmpfs /dev\n'
                '/usr/bin/python3 -B /usr/share/iotbench/sudo-environment/test-session.py '
                '--installed --isolated-fixture\nresult=$?\n'
                'echo IOTBENCH_SUDO_ENV_EXIT=$result\n/bin/poweroff -f\n',
    }
    for name, content in synthetic_files.items():
        path = root / name
        path.write_text(content)
        path.chmod(0o755 if name == 'init' else (0o440 if name == 'etc/sudoers' else
                   0o600 if name == 'etc/shadow' else 0o644))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--isolated-fixture', action='store_true')
    parser.add_argument('--kernel', required=True, type=Path)
    parser.add_argument('--qemu', default='qemu-system-x86_64')
    parser.add_argument('--bios-dir', type=Path)
    parser.add_argument('--log', type=Path, default=Path('/tmp/iotbench-sudo-env-vm.log'))
    arguments = parser.parse_args()
    if not arguments.isolated_fixture or os.uname().machine != 'x86_64':
        parser.error('Requires --isolated-fixture on an x86_64 Linux host')
    if not arguments.kernel.is_file():
        parser.error('A readable Linux kernel is required')
    with tempfile.TemporaryDirectory(prefix='iotbench-sudo-env-vm-') as temporary:
        root = Path(temporary) / 'root'
        populate(root)
        archive = Path(temporary) / 'fixture.cpio.gz'
        initramfs(root, archive)
        command = [arguments.qemu, '-accel', 'tcg', '-m', '512', '-nodefaults',
                   '-display', 'none', '-serial', 'stdio', '-monitor', 'none',
                   '-nic', 'none', '-no-reboot', '-kernel', str(arguments.kernel.resolve()),
                   '-initrd', str(archive), '-append', 'console=ttyS0 quiet panic=-1']
        if arguments.bios_dir:
            command += ['-L', str(arguments.bios_dir.resolve())]
        with arguments.log.open('wb') as log:
            result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=log,
                                    stderr=subprocess.STDOUT, timeout=120)
        transcript = arguments.log.read_text(errors='replace')
        passed = [line for line in transcript.splitlines() if line.startswith('PASS ')]
        if (result.returncode != 0 or '\nIOTBENCH_SUDO_ENV_EXIT=0\n' not in transcript or
                len(passed) != 6):
            raise RuntimeError('Real sudo guest test failed; inspect ' + str(arguments.log))
        for line in passed:
            print(line)
        print('PASS actual sudo-policy VM test; no virtual NIC, host mounts or persistent disk; log ' + str(arguments.log))


if __name__ == '__main__':
    main()
