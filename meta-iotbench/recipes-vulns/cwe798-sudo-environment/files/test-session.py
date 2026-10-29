#!/usr/bin/env python3
"""Run real sudo tests only in an explicitly selected disposable fixture guest."""

import argparse
import os
from pathlib import Path
import pwd
import shutil
import stat
import subprocess
import tempfile

HELPER = Path('@BINDIR@/fixture-sudo-env')
MANIFEST = Path('@DATADIR@/iotbench/sudo-environment/build-config')
POLICY = Path('@SYSCONFDIR@/sudoers.d/iotbench-sudo-environment')
SUDO = Path('@BINDIR@/sudo')
PASSWORD = 'Fixture-Sudo-Only-42'
BUILD_CONFIG = 'IOTBENCH_SUDO_ENV_TEST_ONLY_V1\nmode=fixture\nenabled=1\n'
BASE_ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C', 'HOME': '/nonexistent'}


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def expected(mode='status', config='public', profile='baseline', unlisted='absent'):
    result = 'nominal' if mode == 'status' else 'synthetic-diagnostic'
    return ('FIXTURE_EUID=0\nMODE=' + mode + '\nCONFIG=' + config + '\nPROFILE=' + profile +
            '\nUNLISTED=' + unlisted + '\nRESULT=' + result + '\n')


def invoke(command, environment=None, identity=None):
    def drop_identity():
        os.setgroups([])
        os.setgid(identity.pw_gid)
        os.setuid(identity.pw_uid)

    return subprocess.run([str(item) for item in command],
                          env=dict(BASE_ENV, **(environment or {})),
                          preexec_fn=drop_identity if identity else None,
                          stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True, timeout=10)


def success(result, output):
    check(result.returncode == 0 and result.stdout == output,
          'Unexpected response: ' + repr((result.returncode, result.stdout, result.stderr)))


def denied(result, status=None):
    check(result.returncode != 0 and not result.stdout,
          'Invocation was not denied: ' + repr((result.returncode, result.stdout, result.stderr)))
    if status is not None:
        check(result.returncode == status, 'Unexpected rejection code: ' + result.stderr)


def helper_checks(helper, manifest):
    """Direct C behavior only. This does not establish sudo policy enforcement."""
    success(invoke([helper, '--fixture-test']), expected())
    success(invoke([helper, '--fixture-test'], {'TEST_PROFILE': 'boundary'}),
            expected(profile='boundary'))
    success(invoke([helper, '--fixture-test'], {'FIXTURE_MODE': 'diagnostic',
                   'FIXTURE_CONFIG': PASSWORD, 'TEST_PROFILE': 'boundary'}),
            expected('diagnostic', 'synthetic-fixed', 'boundary'))
    denied(invoke([helper, '--fixture-test'], {'FIXTURE_MODE': 'diagnostic'}), 3)
    denied(invoke([helper, '--fixture-test'], {'FIXTURE_CONFIG': 'incorrect'}), 3)
    for variable in ('FIXTURE_MODE', 'TEST_PROFILE'):
        for value in ('', '/bin/sh', '$(id)', 'status;id', 'x' * 8192):
            denied(invoke([helper, '--fixture-test'], {variable: value}), 2)
    for value in ('/etc/shadow', '/tmp/payload.so', '$(id)', 'x' * 8192):
        denied(invoke([helper, '--fixture-test'], {'FIXTURE_CONFIG': value}), 3)
    for arguments in ([], ['--fixture-test', 'extra'], ['/bin/sh'], ['--shell'],
                      ['--fixture-test', '/etc/shadow']):
        denied(invoke([helper] + arguments), 77)
    # A witness for sudo filtering, never printed as user-controlled text.
    success(invoke([helper, '--fixture-test'], {'FIXTURE_UNLISTED': 'inert'}),
            expected(unlisted='present'))
    print('PASS native helper defaults, allowlisted choices, fixed credential and inert invalid inputs', flush=True)

    original = manifest.read_bytes()
    original_mode = stat.S_IMODE(manifest.stat().st_mode)
    try:
        for content in (b'mode=production\nenabled=1\n',
                        original.replace(b'enabled=1', b'enabled=0'), b'', original + b'extra\n'):
            manifest.write_bytes(content)
            denied(invoke([helper, '--fixture-test']), 77)
        manifest.write_bytes(original)
        manifest.chmod(0o666)
        denied(invoke([helper, '--fixture-test']), 77)
        manifest.chmod(original_mode)
        manifest.unlink()
        denied(invoke([helper, '--fixture-test']), 77)
        manifest.symlink_to('NOTICE')
        denied(invoke([helper, '--fixture-test']), 77)
    finally:
        if manifest.is_symlink():
            manifest.unlink()
        manifest.write_bytes(original)
        manifest.chmod(original_mode)
    print('PASS missing, production, disabled, malformed, writable and symlink manifests refused', flush=True)


def installed():
    check(os.geteuid() == 0, 'Run from the isolated fixture guest root console')
    check(MANIFEST.read_text() == BUILD_CONFIG, 'Explicit fixture build manifest required')
    account = pwd.getpwnam('fixtureenv')
    check(account.pw_uid == 989 and account.pw_gid == 989 and
          account.pw_shell == '/bin/false', 'Unexpected fixture account')
    for path, mode in ((HELPER, 0o755), (POLICY, 0o440), (MANIFEST, 0o644)):
        metadata = path.lstat()
        check(stat.S_ISREG(metadata.st_mode) and metadata.st_uid == metadata.st_gid == 0 and
              stat.S_IMODE(metadata.st_mode) == mode, 'Invalid owner/mode: ' + str(path))
    check(SUDO.stat().st_uid == 0 and SUDO.stat().st_mode & stat.S_ISUID,
          'Real root-owned setuid sudo required inside guest')
    visudo = shutil.which('visudo', path=BASE_ENV['PATH'])
    check(visudo is not None, 'visudo required')
    result = invoke([visudo, '-c'])
    check(result.returncode == 0, 'Installed sudoers validation failed: ' + result.stderr)
    helper_checks(HELPER, MANIFEST)
    denied(invoke([HELPER, '--fixture-test'], identity=account), 77)

    def as_user(arguments, environment=None):
        return invoke([SUDO, '-n'] + arguments, environment, identity=account)

    command = [str(HELPER), '--fixture-test']
    success(as_user(command), expected())
    success(as_user(command, {'TEST_PROFILE': 'boundary'}), expected(profile='boundary'))
    success(as_user(['TEST_PROFILE=boundary'] + command), expected(profile='boundary'))
    variables = {'FIXTURE_MODE': 'diagnostic', 'FIXTURE_CONFIG': PASSWORD, 'TEST_PROFILE': 'boundary'}
    success(as_user(command, variables), expected('diagnostic', 'synthetic-fixed', 'boundary'))
    success(as_user([key + '=' + value for key, value in variables.items()] + command),
            expected('diagnostic', 'synthetic-fixed', 'boundary'))
    denied(as_user(command, {'FIXTURE_MODE': 'diagnostic', 'FIXTURE_CONFIG': 'incorrect'}), 3)
    print('PASS real sudo runs the exact helper as root; preservation and explicit assignments observed', flush=True)

    success(as_user(command, {'FIXTURE_UNLISTED': 'inert'}), expected())
    denied(as_user(['FIXTURE_UNLISTED=inert'] + command))
    denied(as_user(['-E'] + command, {'FIXTURE_UNLISTED': 'inert'}))
    # No dangerous loader payload is supplied or executed.
    denied(as_user(['LD_PRELOAD=/nonexistent-synthetic-library'] + command))
    denied(as_user(['PATH=/nonexistent-synthetic-path'] + command))
    print('PASS unlisted environment removed; unlisted assignments and -E rejected', flush=True)

    shell = shutil.which('sh', path=BASE_ENV['PATH'])
    cat = shutil.which('cat', path=BASE_ENV['PATH'])
    check(shell and cat, 'Guest sh and cat required for denial checks')
    for arguments in ([shell, '-c', 'exit 0'], ['-s'], ['-i'],
                      [str(HELPER)], command + ['extra'], [str(HELPER), '--shell'],
                      ['-u', 'fixtureenv'] + command):
        denied(as_user(arguments))
    # This private file contains a public fake canary, never production data.
    with tempfile.TemporaryDirectory(prefix='iotbench-sudo-env-private-') as temporary:
        directory = Path(temporary)
        directory.chmod(0o755)
        canary = directory / 'production-credentials-canary'
        canary.write_text('SYNTHETIC_ONLY_NO_REAL_CREDENTIALS\n')
        canary.chmod(0o600)
        denied(invoke([cat, canary], identity=account))
        denied(as_user([cat, str(canary)]))
        denied(as_user(command + [str(canary)]))
    print('PASS shells, other commands/runas/arguments and private synthetic credential access denied', flush=True)
    print('PASS Bad SUDO Rights - Allow Changes to Environment Variables (CWE-798)', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed', action='store_true')
    parser.add_argument('--isolated-fixture', action='store_true')
    arguments = parser.parse_args()
    if not arguments.installed or not arguments.isolated_fixture:
        parser.error('Both --installed and --isolated-fixture are required; use a disposable guest')
    installed()


if __name__ == '__main__':
    main()
