#!/usr/bin/env python3
"""SSH policy fixture checks: offline, native OpenSSH, rootfs and optional dashboard."""

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
import os

# Stage files the way a Yocto build does, whatever umask the caller has.
os.umask(0o022)

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
    panel = root / 'usr/share/router-dashboard/modules/ssh-empty-password-policy/module.php'
    panel.parent.mkdir(parents=True)
    shutil.copyfile(MODULE / 'module.php', panel)
    (root / 'etc/passwd').write_text('root:x:0:0:root:/root:/bin/sh\n')
    (root / 'etc/shadow').write_text('root:!:0:0:99999:7:::\n')
    check(validate_rootfs(root), 'Staged rootfs validation failed')
    panel.unlink()
    rejected(lambda: validate_rootfs(root))
    shutil.copyfile(MODULE / 'module.php', panel)
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
    check("validator['validate_rootfs'](d.getVar('IMAGE_ROOTFS')" in guards,
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


class DashboardTokenParser(HTMLParser):
    token = None

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'meta' and values.get('name') == 'dashboard-token':
            self.token = values.get('content')


def dashboard_test(base):
    base = base.rstrip('/')
    with urllib.request.urlopen(base + '/', timeout=15) as response:
        page = response.read().decode()
    token = DashboardTokenParser()
    token.feed(page)
    check(token.token is not None, 'Dashboard token missing')
    check('data-action="ssh_password_policy"' in page, 'SSH policy panel missing')

    def operation(payload, expected_status=200, supplied_token=None):
        request = urllib.request.Request(
            base + '/api.php',
            data=json.dumps(dict(action='ssh_password_policy', **payload)).encode(),
            headers={'Content-Type': 'application/json',
                     'X-Dashboard-Token': token.token if supplied_token is None else supplied_token},
        )
        try:
            response = urllib.request.urlopen(request, timeout=15)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            result = json.load(response)
            check(response.status == expected_status, f'Unexpected HTTP status: {result}')
            check(result.get('ok') is (expected_status == 200), f'Unexpected result: {result}')
        return result

    for _ in range(2):
        installed = operation({'policy': 'firmware', 'password': ''})
        corrected = operation({'policy': 'corrected', 'password': ''})
        check(installed['decision'] == 'POLICY_PERMITS_EMPTY_PASSWORD', 'Empty password not permitted')
        check(installed['permitted_by_policy'] is True and installed['password_empty'] is True,
              'Installed empty-password result mismatch')
        check(corrected['decision'] == 'POLICY_REJECTS_EMPTY_PASSWORD', 'Corrected control failed')
        check(corrected['permitted_by_policy'] is False and corrected['password_empty'] is True,
              'Corrected empty-password result mismatch')
        check('PermitEmptyPasswords=yes' in installed['output'], 'Installed policy unexpectedly changed')
        check('PermitEmptyPasswords=no' in corrected['output'], 'Control policy not applied')
        for result in (installed, corrected):
            check('PasswordAuthentication=yes' in result['output'] and
                  'PermitRootLogin=no' in result['output'], 'Other policy values changed')
    for mode in ('firmware', 'corrected'):
        for candidate in ('manual-policy-check-42', ' ', 'A' * 128):
            result = operation({'policy': mode, 'password': candidate})
            check(result['decision'] == 'POLICY_PERMITS_NONEMPTY_PASSWORD' and
                  result['permitted_by_policy'] is True and result['password_empty'] is False,
                  'Nonempty input was treated as empty')
            if candidate == 'manual-policy-check-42':
                check(candidate not in json.dumps(result), 'Candidate password leaked in result')
    for payload in ({'policy': 'invalid'}, {'policy': []}, {'policy': None},
                    {'password': []}, {'password': None}, {'password': 42},
                    {'password': 'A' * 129}, {'password': 'a\0b'}):
        operation(payload, expected_status=422)
    operation({'password': ''}, expected_status=403, supplied_token='invalid')
    check(operation({'password': ''})['decision'] == 'POLICY_PERMITS_EMPTY_PASSWORD',
          'Corrected-control requests changed the active configuration')
    print('PASS dashboard: empty/nonempty inputs, corrected control, repeated requests, limits and CSRF')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rootfs', type=Path, help='extracted generated fixture rootfs (read only)')
    parser.add_argument('--sshd', help='compatible native host sshd; auto-detected by default')
    parser.add_argument('--skip-openssh', action='store_true', help='run portable checks only')
    parser.add_argument('--url', help='also check the read-only policy panel on a running firmware')
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
        if args.url:
            dashboard_test(args.url)


if __name__ == '__main__':
    try:
        main()
    except (AssertionError, OSError, ValueError, subprocess.CalledProcessError) as error:
        detail = getattr(error, 'stderr', None) or str(error)
        raise SystemExit(f'FAIL: {detail}') from error
