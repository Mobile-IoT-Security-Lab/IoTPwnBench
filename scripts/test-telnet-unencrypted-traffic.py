#!/usr/bin/env python3
"""Validate Telnet source integration, build gates, staged sessions or an extracted rootfs."""

import argparse
import ast
import json
import os
from pathlib import Path
import runpy
import stat
import tempfile
import textwrap

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / 'meta-iotbench'
if not LAYER.is_dir():
    LAYER = Path('/opt/yocto/layers/meta-iotbench')
SLUG = 'cwe798-unencrypted-traffic'
SOURCE = LAYER / 'recipes-vulns' / SLUG / 'files'
BUILD = runpy.run_path(str(SOURCE / 'fixture-build.py'))
TEST = runpy.run_path(str(SOURCE / 'test-session.py'))
check = TEST['check']


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
    check('IOTBENCH_VULN_INSTALL = "' + SLUG + '"' in common, 'Wrong scenario package')
    truth = json.loads((SOURCE / 'ground-truth.json').read_text())
    check(truth['primary_cwe'] == 'CWE-798' and truth['related_cwes'] == ['CWE-287', 'CWE-276']
          and truth['single_scenario'] is True, 'Incorrect single-scenario ground truth')
    service_source = (SOURCE / 'fixture-telnet.py').read_text()
    tree = ast.parse(service_source)
    imports = {item.names[0].name for item in ast.walk(tree) if isinstance(item, ast.Import)}
    check(imports == {'argparse', 'json', 'signal', 'socket', 'time'}, 'Unexpected service modules')
    for symbol, value in (('FIXTURE_USER', truth['username']), ('FIXTURE_PASSWORD', truth['password']),
                          ('LOOPBACK', '127.0.0.1')):
        matches = [node.value.s for node in tree.body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == symbol for target in node.targets)]
        check(matches == [value], 'Missing hard-coded fixture symbol ' + symbol)
    check('listener.bind((LOOPBACK, arguments.port))' in service_source, 'Unfixed bind address')
    check('return bool(username) and password == FIXTURE_PASSWORD' in service_source,
          'CWE-287 password-only sink not found')
    unit = (SOURCE / 'iotbench-telnet.service').read_text()
    for expected in ('User=nobody', 'PrivateNetwork=yes', 'NoNewPrivileges=yes',
                     'ConditionPathExists=/run/iotbench-telnet-test', 'Restart=no',
                     'ProtectSystem=strict', 'RestrictAddressFamilies=AF_INET'):
        check(expected in unit, 'Missing unit safeguard ' + expected)
    check('[Install]' not in unit, 'Fixture must not have boot enablement')
    print('PASS static CWE evidence, service isolation and all {} device recipes'.format(len(devices)), flush=True)

    # Exercise both actual recipe Python guard bodies with minimal metadata stubs.
    # This is an offline policy check, not a claim that BitBake has parsed a build.
    package = LAYER / 'recipes-vulns' / SLUG / (SLUG + '_1.0.bb')
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


def inspect_rootfs(root):
    root = Path(root)
    data = root / 'usr/share/iotbench/unencrypted-traffic'
    auth = root / 'etc/iotbench/telnet-auth.json'
    helper = root / 'usr/bin/fixture-telnet'
    check(stat.S_IMODE(auth.stat().st_mode) == 0o666, 'Missing intentional CWE-276 mode')
    check(json.loads(auth.read_text()) == json.loads((SOURCE / 'telnet-auth.json').read_text()),
          'Wrong installed authentication policy')
    check(stat.S_IMODE(helper.stat().st_mode) == 0o755, 'Incorrect service executable mode')
    build = json.loads((data / 'build-config.json').read_text())
    BUILD['validate_build'](build['mode'], '1' if build['enabled'] is True else '0', build['machine'])
    check('Path(\'/usr/share/iotbench/unencrypted-traffic\')' in helper.read_text(),
          'Rootfs contains host-staged paths')
    for name in ('NOTICE', 'LICENSE', 'ground-truth.json', 'test-session.py'):
        check((data / name).read_bytes() == (SOURCE / name).read_bytes(), 'Installed asset differs: ' + name)
    units = list((root / 'usr/lib/systemd/system').glob('iotbench-telnet.service'))
    units += list((root / 'lib/systemd/system').glob('iotbench-telnet.service'))
    check(units, 'Missing disabled unit')
    for unit in units:
        check('[Install]' not in unit.read_text(), 'Boot enablement present')
    check(not (root / 'run/iotbench-telnet-test').exists(), 'Runtime opt-in marker preinstalled')
    for base in (root / 'etc/systemd/system', root / 'usr/lib/systemd/system', root / 'lib/systemd/system'):
        for entry in base.glob('*.wants/iotbench-telnet.service'):
            raise AssertionError('Unexpected boot link: ' + str(entry))
    print('PASS extracted rootfs service, test build manifest, assets, permissions and disabled startup', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--static', action='store_true')
    choice.add_argument('--local', action='store_true')
    choice.add_argument('--rootfs', type=Path)
    parser.add_argument('--isolated-fixture', action='store_true')
    parser.add_argument('--pcap', type=Path)
    parser.add_argument('--require-pcap', action='store_true')
    parser.add_argument('--transcript', type=Path)
    arguments = parser.parse_args()
    if arguments.local and not arguments.isolated_fixture:
        parser.error('--local requires explicit --isolated-fixture')
    if not arguments.local and (arguments.pcap or arguments.require_pcap or arguments.transcript):
        parser.error('Traffic options require --local')
    integration()
    if arguments.rootfs:
        inspect_rootfs(arguments.rootfs)
    if arguments.local:
        with tempfile.TemporaryDirectory(prefix='iotbench-telnet-local-') as temporary:
            root = Path(temporary)
            root.chmod(0o755)
            BUILD['stage'](root, 'fixture', '1', 'qemuarm64')
            TEST['run_tests'](root, arguments.pcap, arguments.require_pcap, arguments.transcript)


if __name__ == '__main__':
    main()
