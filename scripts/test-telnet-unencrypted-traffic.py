#!/usr/bin/env python3
"""Offline native Telnet integration/build checks; runtime testing is manual in QEMU."""

import argparse
import json
from pathlib import Path
import runpy
import tempfile
import textwrap

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / 'meta-iotbench'
if not LAYER.is_dir():
    LAYER = Path('/opt/yocto/layers/meta-iotbench')
SLUG = 'cwe798-unencrypted-traffic'
SOURCE = LAYER / 'recipes-vulns' / SLUG / 'files'
BUILD = runpy.run_path(str(SOURCE / 'fixture-build.py'))


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def rejected(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError('Production/disabled/non-QEMU build accepted')


def recipe_python(path, name):
    content = path.read_text()
    marker = 'python ' + name + '() {\n'
    return textwrap.dedent(content.split(marker, 1)[1].split('\n}', 1)[0])


def integration():
    devices = sorted(p.parent.name for p in (LAYER / 'recipes-devices').glob('*/device-*.inc'))
    recipes = LAYER / 'recipes-images'
    found = sorted(p.name[len('iotbench-'):-len('-' + SLUG + '.bb')]
                   for p in recipes.glob('iotbench-*-' + SLUG + '.bb'))
    check(devices and devices == found, 'Missing/extra Telnet device image recipes')
    for device in devices:
        text = (recipes / ('iotbench-' + device + '-' + SLUG + '.bb')).read_text()
        for expected in ('require recipes-images/iotbench-image.inc',
                         'require recipes-devices/{0}/device-{0}.inc'.format(device),
                         'require recipes-images/iotbench-unencrypted-traffic.inc'):
            check(expected in text, 'Incorrect image integration: ' + device)
    common = (recipes / 'iotbench-unencrypted-traffic.inc').read_text()
    check('IOTBENCH_VULN_INSTALL = "' + SLUG + '${IOTBENCH_TWIN_SUFFIX}"' in common, 'Wrong scenario package')
    truth = json.loads((SOURCE / 'ground-truth.json').read_text())
    check(truth['demonstrated_cwes'] == ['CWE-319', 'CWE-798']
          and truth['account_privileged'] is False, 'Incorrect native-service ground truth')
    unit = (SOURCE / 'iotbench-telnet.service').read_text()
    for expected in ('/telnetd -F -b 127.0.0.1:2323 -l /bin/login', 'PrivateNetwork=yes',
                     'ConditionPathExists=/run/iotbench-telnet-test', 'Restart=no',
                     'ProtectSystem=strict', 'RestrictAddressFamilies=AF_INET AF_UNIX',
                     'CapabilityBoundingSet=CAP_CHOWN CAP_FOWNER CAP_SETUID CAP_SETGID'):
        check(expected in unit, 'Missing unit safeguard ' + expected)
    check('[Install]' not in unit, 'Fixture must not have boot enablement')
    busybox = LAYER / 'recipes-core/busybox'
    fragment = (busybox / 'files/iotbench-telnet.cfg').read_text()
    for setting in ('CONFIG_TELNET=y', 'CONFIG_TELNETD=y', 'CONFIG_FEATURE_TELNETD_STANDALONE=y'):
        check(setting in fragment.splitlines(), 'Missing native applet: ' + setting)
    append = (busybox / 'busybox_%.bbappend').read_text()
    check("d.getVar('IOTBENCH_ENABLE_TELNET_FIXTURE') == '1'" in append
          and "d.getVar('IOTBENCH_BUILD_MODE') == 'fixture'" in append,
          'BusyBox Telnet config must require opt-in and fixture mode')
    print('PASS native Telnet integration, service isolation and all {} device recipes'.format(len(devices)), flush=True)

    # Exercise both actual recipe Python guard bodies with minimal metadata stubs.
    # This is an offline policy check, not a claim that BitBake has parsed a build.
    package = LAYER / 'recipes-vulns' / SLUG / (SLUG + '_1.0.bb')
    package_text = package.read_text()
    for expected in ('inherit python3native features_check useradd', '--shell /bin/sh',
                     '--gid maintenance', 'busybox curl tcpdump util-linux-nsenter'):
        check(expected in package_text, 'Missing native-login dependency/account: ' + expected)
    package_code = recipe_python(package, '__anonymous')
    image_code = recipe_python(recipes / 'iotbench-unencrypted-traffic.inc', 'iotbench_telnet_fixture_guard')

    class SkipRecipe(ValueError):
        pass

    class Parse:
        @staticmethod
        def mark_dependency(data, path):
            check(Path(path).is_file(), 'Missing shared guard dependency')

    Parse.SkipRecipe = SkipRecipe

    class BB:
        parse = Parse

        @staticmethod
        def fatal(message):
            raise ValueError(message)

    class Metadata:
        def __init__(self, mode, enabled, machine):
            self.values = {'IOTBENCH_BUILD_MODE': mode, 'IOTBENCH_ENABLE_TELNET_FIXTURE': enabled,
                           'MACHINE': machine, 'THISDIR': str(package.parent)}

        def getVar(self, key):
            return self.values.get(key)

    with tempfile.TemporaryDirectory(prefix='iotbench-telnet-build-gates-') as temporary:
        invalid_output = Path(temporary) / 'must-not-exist'
        cases = [('fixture', '1', machine, True) for machine in BUILD['MACHINES']]
        cases += [(mode, enabled, machine, False)
                  for mode, enabled, machine in (
                      ('production', '0', 'qemuarm64'), ('production', '1', 'qemuarm64'),
                      ('fixture', '0', 'qemuarm64'), ('fixture', '1', 'production-board'),
                      ('', '1', 'qemuarm64'), ('fixture', 'yes', 'qemuarm64'))]
        for mode, enabled, machine, allowed in cases:
            actions = [lambda: BUILD['validate_build'](mode, enabled, machine)]
            for code in (package_code, image_code):
                actions.append(lambda code=code: exec(code, {'d': Metadata(mode, enabled, machine), 'bb': BB}))
            for action in actions:
                action() if allowed else rejected(action)
            if not allowed:
                rejected(lambda: BUILD['stage'](invalid_output, mode, enabled, machine))
        check(not invalid_output.exists(), 'Rejected build wrote fixture files')
    print('PASS shared build policy and both recipe guards: production, opt-in and machine matrix (offline)', flush=True)
    with tempfile.TemporaryDirectory(prefix='iotbench-telnet-stage-') as temporary:
        root = Path(temporary)
        BUILD['stage'](root, 'fixture', '1', 'qemuarm64', target_paths=True)
        staged = root / 'usr/lib/systemd/system/iotbench-telnet.service'
        check('ExecStart=/usr/sbin/telnetd ' in staged.read_text(), 'Native daemon path not rendered')
        check(not (root / 'usr/bin/fixture-telnet').exists(), 'Simulated daemon was staged')
    print('PASS native service staging (does not compile or execute BusyBox)', flush=True)


def inspect_rootfs(root):
    root = Path(root)
    data = root / 'usr/share/iotbench/unencrypted-traffic'
    build = json.loads((data / 'build-config.json').read_text())
    BUILD['validate_build'](build['mode'], '1' if build['enabled'] is True else '0', build['machine'])
    for name in ('NOTICE', 'LICENSE', 'ground-truth.json'):
        check((data / name).read_bytes() == (SOURCE / name).read_bytes(), 'Installed asset differs: ' + name)
    for obsolete in ('usr/bin/fixture-telnet', 'etc/iotbench/telnet-auth.json'):
        check(not (root / obsolete).exists(), 'Obsolete simulated service installed: ' + obsolete)
    passwd = (root / 'etc/passwd').read_text().splitlines()
    account = next(line.split(':') for line in passwd if line.startswith('maintenance:'))
    check(int(account[2]) != 0 and account[-1] == '/bin/sh', 'Maintenance account must be unprivileged')
    shadow = (root / 'etc/shadow').read_text().splitlines()
    credential = next(line.split(':')[1] for line in shadow if line.startswith('maintenance:'))
    check(credential.startswith('$6$iottelnet$') and credential in
          (LAYER / 'recipes-vulns' / SLUG / (SLUG + '_1.0.bb')).read_text().replace('\\$', '$'),
          'Installed maintenance credential differs from recipe')
    units = list((root / 'usr/lib/systemd/system').glob('iotbench-telnet.service'))
    units += list((root / 'lib/systemd/system').glob('iotbench-telnet.service'))
    check(units, 'Missing disabled unit')
    for unit in units:
        check('[Install]' not in unit.read_text(), 'Boot enablement present')
    check(not (root / 'run/iotbench-telnet-test').exists(), 'Runtime opt-in marker preinstalled')
    for base in (root / 'etc/systemd/system', root / 'usr/lib/systemd/system', root / 'lib/systemd/system'):
        for entry in base.glob('*.wants/iotbench-telnet.service'):
            raise AssertionError('Unexpected boot link: ' + str(entry))
    print('PASS extracted rootfs native-login account, assets and disabled startup (offline)', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--static', action='store_true')
    choice.add_argument('--rootfs', type=Path)
    arguments = parser.parse_args()
    integration()
    if arguments.rootfs:
        inspect_rootfs(arguments.rootfs)


if __name__ == '__main__':
    main()
