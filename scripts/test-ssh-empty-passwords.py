#!/usr/bin/env python3
"""Offline SSH fixture tests, optional OpenSSH -t/-T, and extracted-rootfs checks."""

import argparse
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / 'meta-iotbench/recipes-vulns/cwe521-permit-empty-passwords/files'
VALIDATOR = runpy.run_path(str(MODULE / 'validate_config.py'))
check = VALIDATOR['check']
validate_config = VALIDATOR['validate_config']
validate_rootfs = VALIDATOR['validate_rootfs']


def rejected(action):
    try:
        action()
    except (AssertionError, ValueError, OSError):
        return
    raise AssertionError('Invalid fixture was accepted')


def self_test(work):
    source = (MODULE / 'sshd_config').read_text()
    positive = work / 'positive.conf'
    negative = work / 'negative.conf'
    positive.write_text(source)
    negative.write_text(source.replace('PermitEmptyPasswords yes', 'PermitEmptyPasswords no'))
    check(validate_config(positive), 'Positive case not detected')
    check(not validate_config(negative, 'no'), 'Negative control flagged vulnerable')
    rejected(lambda: validate_config(negative))
    rejected(lambda: validate_config(positive, 'no'))
    for mutation in (
        source.replace('PermitEmptyPasswords yes', '# PermitEmptyPasswords yes'),
        source + '\nPermitEmptyPasswords no\n',
        source + '\nMatch User root\nPermitEmptyPasswords no\n',
        source + '\nInclude /etc/ssh/sshd_config.d/*.conf\n',
        source.replace('PermitRootLogin no', 'PermitRootLogin yes'),
        source.replace('PasswordAuthentication yes', 'PasswordAuthentication no'),
    ):
        invalid = work / 'invalid.conf'
        invalid.write_text(mutation)
        rejected(lambda: validate_config(invalid))

    root = work / 'staged-rootfs'
    (root / 'etc/ssh').mkdir(parents=True)
    shutil.copyfile(positive, root / 'etc/ssh/sshd_config')
    (root / 'etc/passwd').write_text('root:x:0:0:root:/root:/bin/sh\n')
    (root / 'etc/shadow').write_text('root:!:0:0:99999:7:::\n')
    check(validate_rootfs(root), 'Staged rootfs validation failed')
    (root / 'usr/sbin').mkdir(parents=True)
    for daemon in ('sshd', 'dropbear', 'sshd-session'):
        binary = root / 'usr/sbin' / daemon
        binary.touch()
        rejected(lambda: validate_rootfs(root))
        binary.unlink()
    (root / 'etc/init.d').mkdir()
    startup = root / 'etc/init.d/sshd'
    startup.symlink_to('/usr/sbin/sshd')
    rejected(lambda: validate_rootfs(root))
    startup.unlink()
    for database in ('shadow', 'passwd'):
        target = root / 'etc' / database
        saved = target.read_text()
        target.write_text('root::0:0:root:/root:/bin/sh\n')
        rejected(lambda: validate_rootfs(root))
        target.write_text(saved)
    config = root / 'etc/ssh/sshd_config'
    config.unlink()
    rejected(lambda: validate_rootfs(root))
    print('PASS positive/negative policy, ambiguous config rejection, rootfs safeguards (staged test data)')
    return positive, negative


def integration_test():
    layer = REPO / 'meta-iotbench'
    devices = sorted(p.parent.name for p in (layer / 'recipes-devices').glob('*/device-*.inc'))
    check(len(devices) == 11, f'Unexpected supported devices: {devices}')
    images = layer / 'recipes-images'
    expected = {f'iotbench-{d}-cwe521-permit-empty-passwords.bb' for d in devices}
    for device in devices:
        recipe = images / f'iotbench-{device}-cwe521-permit-empty-passwords.bb'
        text = recipe.read_text()
        check(f'require recipes-devices/{device}/device-{device}.inc' in text,
              f'Wrong device integration: {device}')
        check('require recipes-images/iotbench-permit-empty-passwords.inc' in text,
              f'Missing explicit fixture opt-in: {device}')
    # Normal recipes must not reference this package or include. Other benchmark
    # SSH vulnerabilities are separate fixtures and are intentionally untouched.
    for recipe in images.glob('*.bb'):
        if recipe.name not in expected:
            check('permit-empty-passwords' not in recipe.read_text(),
                  f'Fixture leaked into another image: {recipe}')
    guards = (images / 'iotbench-permit-empty-passwords.inc').read_text()
    check('PACKAGE_EXCLUDE += "openssh-sshd dropbear"' in guards,
          'SSH daemon package exclusions missing')
    check('ROOTFS_POSTPROCESS_COMMAND += "iotbench_validate_empty_passwords; "' in guards,
          'Rootfs validation hook missing')
    check("validator['validate_rootfs'](d.getVar('IMAGE_ROOTFS'))" in guards,
          'Rootfs hook does not validate the built filesystem')
    common = (images / 'iotbench-image.inc').read_text()
    check('permit-empty-passwords' not in common, 'Fixture enabled in shared image')
    for path in layer.rglob('*'):
        if path.is_file() and (path.suffix == '.conf' or path.name == 'sshd_config'):
            lines = [line.split('#', 1)[0].strip().lower() for line in path.read_text().splitlines()]
            if any(line.split() == ['permitemptypasswords', 'yes'] for line in lines):
                check(path == MODULE / 'sshd_config', f'Insecure setting outside fixture: {path}')
    print(f'PASS explicit integration for {len(devices)} devices; no leakage into other image/config sources')


def openssh_test(sshd, configs, work):
    keygen = shutil.which('ssh-keygen')
    check(keygen is not None, 'ssh-keygen is required for optional sshd checks')
    key = work / 'host_key'
    subprocess.run([keygen, '-q', '-t', 'ed25519', '-N', '', '-f', str(key)], check=True)
    for config, expected in configs:
        # Only test modes are permitted here: neither opens a listening socket.
        args = [sshd, '-f', str(config.resolve()), '-h', str(key)]
        subprocess.run([*args, '-t'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        result = subprocess.run([*args, '-T'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        effective = dict(line.split(None, 1) for line in result.stdout.splitlines() if ' ' in line)
        check(effective.get('permitemptypasswords') == expected,
              f'Wrong effective empty-password policy for {config}')
        check(effective.get('passwordauthentication') == 'yes', 'Password policy disabled')
        check(effective.get('permitrootlogin') == 'no', 'Root login enabled')
        print(f'PASS sshd -t and -T: {config.name}, permitemptypasswords {expected}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rootfs', type=Path, help='extracted generated fixture rootfs (read only)')
    parser.add_argument('--sshd', help='compatible native host sshd; auto-detected by default')
    parser.add_argument('--skip-openssh', action='store_true', help='run portable checks only')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='iotbench-ssh-config-') as directory:
        work = Path(directory)
        positive, negative = self_test(work)
        integration_test()
        configs = [(positive, 'yes'), (negative, 'no')]
        if args.rootfs:
            validate_rootfs(args.rootfs)
            configs.append((args.rootfs / 'etc/ssh/sshd_config', 'yes'))
            print(f'PASS generated rootfs configuration and isolation: {args.rootfs}')
        sshd = args.sshd or shutil.which('sshd')
        if not sshd and Path('/usr/sbin/sshd').is_file():
            sshd = '/usr/sbin/sshd'
        if sshd and not args.skip_openssh:
            openssh_test(str(Path(sshd).resolve()), configs, work)
        else:
            print('SKIP OpenSSH -t/-T: disabled or compatible host binary not available')


if __name__ == '__main__':
    try:
        main()
    except (AssertionError, OSError, ValueError, subprocess.CalledProcessError) as error:
        detail = getattr(error, 'stderr', None) or str(error)
        raise SystemExit(f'FAIL: {detail}') from error
