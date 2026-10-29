#!/usr/bin/env python3
"""Offline integration/build-gate checks, native C tests, or extracted rootfs inspection.

Native tests use an isolated rootless user/network namespace, never host sudo.
Real sudo tests are packaged as test-session.py for a disposable fixture guest.
"""

import argparse
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / 'meta-iotbench'
if not LAYER.is_dir():
    LAYER = Path('/opt/yocto/layers/meta-iotbench')
SLUG = 'cwe798-sudo-environment'
SOURCE = LAYER / 'recipes-vulns' / SLUG / 'files'
BUILD = runpy.run_path(str(SOURCE / 'fixture-build.py'))
TEST = runpy.run_path(str(SOURCE / 'test-session.py'))
check = TEST['check']


def rejected(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError('Invalid build configuration accepted')


def recipe_python(path, name):
    content = path.read_text()
    marker = 'python ' + name + '() {\n'
    return textwrap.dedent(content.split(marker, 1)[1].split('\n}', 1)[0])


def integration():
    devices = sorted(path.parent.name for path in (LAYER / 'recipes-devices').glob('*/device-*.inc'))
    images = LAYER / 'recipes-images'
    found = sorted(path.name[len('iotbench-'):-len('-' + SLUG + '.bb')]
                   for path in images.glob('iotbench-*-' + SLUG + '.bb'))
    check(devices and devices == found, 'Missing/extra device images')
    for device in devices:
        content = (images / ('iotbench-' + device + '-' + SLUG + '.bb')).read_text()
        for require in ('require recipes-images/iotbench-image.inc',
                        'require recipes-devices/{0}/device-{0}.inc'.format(device),
                        'require recipes-images/iotbench-sudo-environment.inc'):
            check(require in content, 'Incorrect device integration: ' + device)
    common = images / 'iotbench-sudo-environment.inc'
    check('IOTBENCH_VULN_INSTALL = "' + SLUG + '"' in common.read_text(), 'Unexpected scenario package')
    truth = json.loads((SOURCE / 'ground-truth.json').read_text())
    check(truth['catalog_cwe'] == 'CWE-798' and truth['single_scenario'] is True, 'Scenario label')
    check(truth['environment_allowlist'] == ['FIXTURE_MODE', 'FIXTURE_CONFIG', 'TEST_PROFILE'], 'Allowlist')
    check(truth['synthetic_password'] == TEST['PASSWORD'], 'Credential mismatch')
    policy = (SOURCE / 'iotbench-sudo-environment').read_text()
    directives = [line for line in policy.splitlines() if line and not line.startswith('#')]
    check(directives == [
        'Defaults:fixtureenv env_reset, !setenv',
        'Defaults:fixtureenv env_keep = "FIXTURE_MODE FIXTURE_CONFIG TEST_PROFILE"',
        'Defaults:fixtureenv !env_check',
        'Defaults:fixtureenv secure_path = "@BINDIR@:@BASE_BINDIR@"',
        'fixtureenv ALL=(root) NOPASSWD: NOSETENV: @BINDIR@/fixture-sudo-env --fixture-test',
    ], 'Unexpected sudo policy scope')
    source = (SOURCE / 'fixture-sudo-env.c').read_text()
    check('static const char FIXTURE_PASSWORD[] = "' + truth['synthetic_password'] + '";' in source,
          'CWE-798 fixed diagnostic credential missing')
    check('strcmp(config, FIXTURE_PASSWORD)' in source, 'Credential comparison missing')
    for variable in truth['environment_allowlist']:
        check('setting("' + variable + '"' in source, 'Missing environment input')
    forbidden = r'\b(system|popen|exec\w*|dlopen|socket|bind|listen|setuid|setgid|chmod|chown)\s*\('
    check(not re.search(forbidden, source), 'Helper has a forbidden execution/system-mutation API')
    check(re.findall(r'\bopen\(([^,]+),', source) == ['FIXTURE_MANIFEST'], 'Unexpected file input')
    print('PASS static sudo policy, CWE-798 data flow and all {} device recipes'.format(len(devices)), flush=True)

    package = LAYER / 'recipes-vulns' / SLUG / (SLUG + '_1.0.bb')
    package_code = recipe_python(package, '__anonymous')
    image_code = recipe_python(common, 'iotbench_sudo_env_fixture_guard')

    class SkipRecipe(ValueError):
        pass

    class Parse:
        @staticmethod
        def mark_dependency(data, path):
            check(Path(path).is_file(), 'Missing shared build guard')

    Parse.SkipRecipe = SkipRecipe

    class BB:
        parse = Parse

        @staticmethod
        def fatal(message):
            raise ValueError(message)

    class Metadata:
        def __init__(self, mode, enabled, machine):
            self.values = {'IOTBENCH_BUILD_MODE': mode, 'IOTBENCH_ENABLE_SUDO_ENV_FIXTURE': enabled,
                           'MACHINE': machine, 'THISDIR': str(SOURCE.parent)}

        def getVar(self, name):
            return self.values.get(name)

    for mode in ('production', 'fixture', None):
        for enabled in ('0', '1', None):
            for machine in BUILD['MACHINES'] + ('production-board', None):
                valid = mode == 'fixture' and enabled == '1' and machine in BUILD['MACHINES']
                data = Metadata(mode, enabled, machine)
                for code in (package_code, image_code):
                    action = lambda: exec(code, {'d': data, 'bb': BB})
                    action() if valid else rejected(action)
                with tempfile.TemporaryDirectory(prefix='iotbench-sudo-env-gate-') as temporary:
                    output = Path(temporary) / 'disabled'
                    if not valid:
                        rejected(lambda: BUILD['stage'](output, mode, enabled, machine))
                        check(not output.exists(), 'Invalid build wrote fixture files')
    recipe = package.read_text()
    for expected in ('--shell /bin/false --password', '-DIOTBENCH_SUDO_ENV_FIXTURE_ENABLED=1',
                     'do_compile[vardeps]', 'do_install[vardeps]', '--target-paths'):
        check(expected in recipe, 'Missing recipe isolation: ' + expected)
    print('PASS actual recipe Python guards and staging reject production/disabled/non-QEMU configurations', flush=True)

    # Syntax-check the fixture fragment without installing it or using host sudo.
    visudo = shutil.which('visudo', path='/usr/sbin:/sbin:/usr/bin:/bin')
    check(visudo is not None, 'visudo is required for policy syntax validation')
    with tempfile.TemporaryDirectory(prefix='iotbench-sudo-env-policy-') as temporary:
        path = Path(temporary) / 'sudoers'
        path.write_text(policy.replace('@BINDIR@', '/usr/bin').replace('@BASE_BINDIR@', '/bin'))
        result = subprocess.run([visudo, '-c', '-f', str(path)], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, universal_newlines=True, timeout=10)
        check(result.returncode == 0, 'visudo rejected fixture: ' + result.stderr)
    print('PASS native visudo policy syntax (host policy unchanged)', flush=True)


def local(namespace_child):
    if not namespace_child:
        subprocess.run(['unshare', '--user', '--map-root-user', '--net', sys.executable,
                        str(Path(__file__).resolve()), '--local', '--isolated-fixture',
                        '--namespace-child'], check=True, timeout=60)
        return
    check(os.geteuid() == 0, 'Native helper checks need namespace root')
    uid_map = Path('/proc/self/uid_map').read_text().split()
    check(len(uid_map) == 3 and uid_map[0] == '0' and uid_map[2] == '1',
          'Native tests require a rootless single-user namespace')
    with tempfile.TemporaryDirectory(prefix='iotbench-sudo-env-native-') as temporary:
        output = Path(temporary) / 'stage'
        BUILD['stage'](output, 'fixture', '1', 'qemuarm64')
        helper = output / 'usr/bin/fixture-sudo-env'
        manifest = output / 'usr/share/iotbench/sudo-environment/build-config'
        check(TEST['PASSWORD'].encode() in helper.read_bytes(), 'Compiled CWE-798 credential absent')
        TEST['helper_checks'](helper, manifest)
        # Without the explicit compile-time opt-in even a forged runtime marker
        # and namespace-root execution cannot activate the helper.
        production = Path(temporary) / 'production-helper'
        subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                        str(SOURCE / 'fixture-sudo-env.c'), '-o', str(production)], check=True)
        TEST['denied'](TEST['invoke']([production, '--fixture-test']), 77)
        check(TEST['PASSWORD'].encode() not in production.read_bytes(), 'Production build contains credential')
        imports = subprocess.check_output(['nm', '-u', str(helper)], universal_newlines=True)
        check(not re.search(r'\b(system|popen|exec\w*|dlopen|socket|setuid|setgid)@', imports),
              'Compiled helper imports forbidden APIs')
        print('PASS production-compiled helper refuses activation; binary has no command/library/socket APIs', flush=True)
    print('PASS native-only checks complete; real sudo enforcement requires the packaged guest test', flush=True)


def rootfs(root):
    root = root.resolve()
    data = root / 'usr/share/iotbench/sudo-environment'
    check((data / 'build-config').read_text() == BUILD['MANIFEST'], 'Invalid runtime manifest')
    for path, permissions in ((root / 'usr/bin/fixture-sudo-env', 0o755),
                              (root / 'etc/sudoers.d/iotbench-sudo-environment', 0o440),
                              (data / 'build-config', 0o644)):
        info = path.lstat()
        check(stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode) == permissions,
              'Unexpected installed type/mode: ' + str(path))
    expected = (SOURCE / 'iotbench-sudo-environment').read_text()
    expected = expected.replace('@BINDIR@', '/usr/bin').replace('@BASE_BINDIR@', '/bin')
    check((root / 'etc/sudoers.d/iotbench-sudo-environment').read_text() == expected, 'Installed policy differs')
    for name in ('NOTICE', 'LICENSE', 'ground-truth.json', 'fixture-sudo-env.c', 'fixture-build.py', 'test-session.py'):
        check((data / name).is_file(), 'Missing packaged artifact: ' + name)
    check(TEST['PASSWORD'].encode() in (root / 'usr/bin/fixture-sudo-env').read_bytes(), 'Missing binary credential')
    check(not list((root / 'etc/systemd').glob('**/*sudo-env*')), 'Unexpected fixture startup hook')
    print('PASS extracted rootfs assets/modes/policy and compiled credential (no guest execution)', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument('--static', action='store_true')
    selection.add_argument('--local', action='store_true')
    selection.add_argument('--rootfs', type=Path)
    parser.add_argument('--isolated-fixture', action='store_true')
    parser.add_argument('--namespace-child', action='store_true', help=argparse.SUPPRESS)
    arguments = parser.parse_args()
    if arguments.static:
        integration()
    elif arguments.rootfs:
        rootfs(arguments.rootfs)
    else:
        if not arguments.isolated_fixture:
            parser.error('--local requires --isolated-fixture')
        local(arguments.namespace_child)


if __name__ == '__main__':
    main()
