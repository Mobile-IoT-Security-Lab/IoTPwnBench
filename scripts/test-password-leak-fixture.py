#!/usr/bin/env python3
"""Deterministic offline Password Leak regression; explicit fixture context only."""

import argparse
import base64
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
import textwrap

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / 'meta-iotbench'
SOURCE = LAYER / 'recipes-vulns/cwe798-password-leak/files'
LIB = runpy.run_path(str(SOURCE / 'fixture-lib.py'))
BUILD = runpy.run_path(str(SOURCE / 'fixture-build.py'))
INVENTORY = json.loads((SOURCE / 'synthetic-inventory.json').read_text())
EXPECTED = json.loads((SOURCE / 'expected-findings.json').read_text())
GROUPS = []


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def passed(message):
    GROUPS.append(message)
    print('PASS ' + message, flush=True)


def rejected(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError('Invalid build context accepted')


def stage(output, variant, machine='qemuarm64', datadir='/usr/share'):
    return BUILD['stage'](output, 'fixture', '1', machine, variant, datadir)


def verify(rootfs, variant, datadir='/usr/share'):
    root = rootfs / datadir.lstrip('/') / 'iotbench/password-leak' / variant
    check(sorted(p.name for p in root.parent.iterdir()) == [variant], 'Mixed variants')
    item = INVENTORY[variant]
    findings = LIB['scan'](root)
    for finding in findings:
        finding['path'] = (root.relative_to(rootfs) / finding['path']).as_posix()
    check(len(findings) == 1, 'Expected exactly one credential: ' + repr(findings))
    finding = findings[0]
    expected = dict(EXPECTED[variant])
    expected['path'] = (root.relative_to(rootfs) / item['file']).as_posix()
    for field in ('path', 'line', 'field', 'encoding'):
        check(finding[field] == expected[field], 'Manifest mismatch: ' + field)
    check(finding['value'] == item['value'], 'Unlisted credential in firmware')
    check(hashlib.sha256(finding['value'].encode()).hexdigest() == expected['sha256'],
          'Credential fingerprint differs')
    check(json.loads((root / 'expected-findings.json').read_text()) == [expected],
          'Installed manifest differs')
    for path in [root] + list(root.rglob('*')):
        check(not path.is_symlink(), 'Unexpected symlink')
        check(path.stat().st_mode & 0o7777 == (0o755 if path.is_dir() else 0o644),
              'Unexpected filesystem permissions: ' + str(path))
    # Every raw/encoded credential occurrence must be in the single payload.
    for path in rootfs.rglob('*'):
        if path.is_symlink() or not path.is_file():
            continue
        data = path.read_bytes()
        for other in INVENTORY.values():
            raw = other['value'].encode()
            for representation in (raw, base64.b64encode(raw)):
                if representation in data:
                    check(path == root / item['file'] and other == item,
                          'Credential inventory leaked into another artifact')
        if root in path.parents:
            check(not re.search(rb'(?:https?|ftp|ssh)://', data), 'External endpoint in fixture')
    plain = LIB['scan'](root, decode_base64=False)
    check(len(plain) == (0 if item['encoding'] == 'base64' else 1),
          'Incorrect decoding-disabled behavior')
    return root


def authenticate(root, candidate, enabled=True):
    command = [sys.executable, str(root / 'fixture-auth.py')]
    if enabled:
        command.append('--isolated-fixture')
    return subprocess.run(command, input=candidate + b'\n', stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=10)


def staged_tests(work):
    snapshots = {}
    for variant in LIB['VARIANTS']:
        item = INVENTORY[variant]
        rootfs = work / variant
        root = stage(rootfs, variant)
        verify(rootfs, variant)
        good = authenticate(root, item['value'].encode())
        check(good.returncode == 0 and good.stdout == b'synthetic-auth: accepted\n',
              'Configured credential was not used: ' + variant + good.stderr.decode())
        for candidate in (b'', b'not-a-fixture-credential', item['value'].lower().encode()):
            bad = authenticate(root, candidate)
            check(bad.returncode == 1 and bad.stdout == b'synthetic-auth: rejected\n',
                  'Wrong credential accepted: ' + variant)
        check(authenticate(root, item['value'].encode(), False).returncode == 77,
              'Runtime context opt-in missing')
        check(authenticate(root, b'x' * 4097).returncode == 77, 'Oversized input accepted')
        marker = root / 'build-config.json'
        previous = marker.read_bytes()
        marker.write_text('{"mode":"production"}')
        check(authenticate(root, item['value'].encode()).returncode == 77,
              'Production/malformed marker accepted')
        marker.write_bytes(previous)
        snapshots[variant] = {p.relative_to(rootfs).as_posix(): p.read_bytes()
                              for p in rootfs.rglob('*') if p.is_file()}
        # Rebuilding produces exactly the same files and no environment-dependent paths.
        again = work / (variant + '-again')
        stage(again, variant)
        check(snapshots[variant] == {p.relative_to(again).as_posix(): p.read_bytes()
                                   for p in again.rglob('*') if p.is_file()},
              'Non-deterministic output')
    passed('15 staged variants: exact manifests/inventory, local auth, wrong inputs and deterministic rebuilds')
    passed('plaintext, syntax/case/separator/quoting variants and Base64 on/off scanning')
    passed('no extra secret copies, external endpoints, startup hooks or unsafe permissions')

    # A reference scanner must find an extra secret instead of trusting the manifest.
    rootfs = work / 'conf-password'
    extra = rootfs / 'usr/share/iotbench/password-leak/conf-password/extra.conf'
    for value in ('UNLISTED_SECRET', 'FIXTURE_UNLISTED_SECRET'):
        extra.write_text('password=' + value + '\n')
        check(len(LIB['scan'](extra.parent)) == 2, 'Unexpected credential escaped scanning')
        try:
            verify(rootfs, 'conf-password')
        except AssertionError:
            pass
        else:
            raise AssertionError('Unlisted credential escaped inventory validation')
    extra.unlink()
    check(LIB['scan'](SOURCE / 'negative') == [], 'Negative controls classified as credentials')
    passed('placeholders, documentation and ordinary values remain negative; unlisted credentials fail')

    # Every supported architecture uses the identical stage policy; no cross compiler needed.
    for machine, variant in itertools.product(LIB['MACHINES'], LIB['VARIANTS']):
        rootfs = work / ('matrix-' + machine + '-' + variant)
        stage(rootfs, variant, machine)
        verify(rootfs, variant)
    alternate = work / 'alternate-datadir'
    old_umask = os.umask(0o077)
    try:
        stage(alternate, 'xml-api', datadir='/opt/fixture-data')
    finally:
        os.umask(old_umask)
    verify(alternate, 'xml-api', datadir='/opt/fixture-data')
    passed('75 QEMU machine/variant stages and alternate target datadir')


def policy_tests(work):
    for mode, enabled, machine, variant in itertools.product(
            ('production', 'fixture', '', None), ('0', '1', '', None),
            LIB['MACHINES'] + ('hardware-device', '', None), LIB['VARIANTS'] + ('unknown', '', None)):
        valid = (mode == 'fixture' and enabled == '1'
                 and machine in LIB['MACHINES'] and variant in LIB['VARIANTS'])
        if valid:
            LIB['validate_build'](mode, enabled, machine, variant)
        else:
            rejected(lambda: LIB['validate_build'](mode, enabled, machine, variant))
    for mode, enabled, machine, variant in (
            ('production', '1', 'qemuarm64', 'conf-password'),
            ('fixture', '0', 'qemuarm64', 'conf-password'),
            ('fixture', '1', 'hardware', 'conf-password'),
            ('fixture', '1', 'qemuarm64', 'unknown')):
        output = work / 'refused-output'
        rejected(lambda: BUILD['stage'](output, mode, enabled, machine, variant))
        check(not output.exists(), 'Rejected build wrote files')
    existing = work / 'existing'
    existing.mkdir()
    rejected(lambda: stage(existing, 'conf-password'))
    cli = subprocess.run([sys.executable, str(ROOT / 'scripts/build-password-leak-fixture.py'),
                          '--output', str(work / 'default-cli'), '--variant', 'conf-password'],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
    check(cli.returncode == 2 and not (work / 'default-cli').exists(),
          'Default host build did not reject production context')

    # Mutate an isolated source copy, never the repository's fixture inventory.
    # The shared host/Yocto builder must refuse drift before creating output.
    source = work / 'source-drift' / 'files'
    shutil.copytree(SOURCE, source)
    builder = runpy.run_path(str(source / 'fixture-build.py'))['stage']
    payload = source / 'fixtures/conf-password' / INVENTORY['conf-password']['file']
    manifest = source / 'expected-findings.json'
    negative = source / 'negative/placeholders.conf'
    original_payload = payload.read_bytes()
    original_manifest = manifest.read_bytes()
    original_negative = negative.read_bytes()
    output = work / 'refused-drift'

    def refuse_drift():
        rejected(lambda: builder(output, 'fixture', '1', 'qemuarm64', 'conf-password'))
        check(not output.exists(), 'Source drift wrote firmware files')

    payload.write_bytes(original_payload + b'auth_token=UNLISTED_SECRET\n')
    refuse_drift()
    payload.write_bytes(b'\n' + original_payload)
    refuse_drift()
    payload.write_bytes(original_payload)
    for field, value in (('cwe', 'CWE-200'), ('scenario_count', 2),
                         ('usage', 'stored-only'), ('location', 'incorrect'),
                         ('encoding', 'base64')):
        changed = json.loads(original_manifest)
        changed['conf-password'][field] = value
        manifest.write_text(json.dumps(changed))
        refuse_drift()
    manifest.write_bytes(original_manifest)
    negative.write_bytes(original_negative + b'password=UNLISTED_SECRET\n')
    refuse_drift()
    negative.write_bytes(original_negative)
    # A restored source copy must still build successfully.
    builder(output, 'fixture', '1', 'qemuarm64', 'conf-password')
    verify(output, 'conf-password')
    passed('fail-closed production/disabled/non-QEMU/unknown-variant policy; no rejected-build writes')


def recipe_function(path, name):
    return textwrap.dedent(path.read_text().split('python ' + name + '() {\n', 1)[1].split('\n}', 1)[0])


def integration_tests():
    recipes = LAYER / 'recipes-images'
    devices = sorted(p.parent.name for p in (LAYER / 'recipes-devices').glob('*/device-*.inc'))
    expected = {'iotbench-' + d + '-cwe798-password-leak-' + v + '.bb'
                for d, v in itertools.product(devices, LIB['VARIANTS'])}
    check(expected == {p.name for p in recipes.glob('iotbench-*-cwe798-password-leak-*.bb')
                       if not p.stem.endswith('-fixed')},
          'Missing/extra device/variant image recipes')
    twins = {name[:-len('.bb')] + '-fixed.bb' for name in expected}
    check(twins == {p.name for p in recipes.glob('iotbench-*-cwe798-password-leak-*-fixed.bb')},
          'Missing/extra corrected twin image recipes')
    for device, variant in itertools.product(devices, LIB['VARIANTS']):
        text = (recipes / ('iotbench-' + device + '-cwe798-password-leak-' + variant + '.bb')).read_text()
        for required in ('require recipes-images/iotbench-image.inc',
                         'require recipes-devices/{0}/device-{0}.inc'.format(device),
                         'require recipes-images/iotbench-password-leak.inc',
                         'IOTBENCH_PASSWORD_LEAK_VARIANT = "' + variant + '"'):
            check(required in text, 'Incorrect image/device/variant wiring')
    package = SOURCE.parent / 'cwe798-password-leak.inc'
    for variant in LIB['VARIANTS']:
        text = (SOURCE.parent / ('cwe798-password-leak-' + variant + '_1.0.bb')).read_text()
        check(text == 'require cwe798-password-leak.inc\nIOTBENCH_PASSWORD_LEAK_VARIANT = "'
              + variant + '"\n', 'Incorrect package variant wiring')
    for path in recipes.glob('*.bb'):
        if path.name not in expected and path.name not in twins:
            check('cwe798-password-leak' not in path.read_text(), 'Fixture in another image')

    class SkipRecipe(ValueError):
        pass

    class Parse:
        @staticmethod
        def mark_dependency(data, path):
            check(Path(path).is_file(), 'Missing recipe policy dependency')

    Parse.SkipRecipe = SkipRecipe

    class BB:
        parse = Parse

        @staticmethod
        def fatal(message):
            raise ValueError(message)

    class Data:
        def __init__(self, mode, enabled, machine, variant, extra=False):
            package = 'cwe798-password-leak-' + variant
            self.values = dict(IOTBENCH_BUILD_MODE=mode, IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE=enabled,
                               MACHINE=machine, IOTBENCH_PASSWORD_LEAK_VARIANT=variant,
                               THISDIR=str(SOURCE.parent), IOTBENCH_PASSWORD_LEAK_LAYER=str(LAYER),
                               IOTBENCH_VULN_INSTALL=package, IOTBENCH_TWIN_SUFFIX='',
                               IMAGE_INSTALL=package + (' cwe999-other' if extra else ''))

        def getVar(self, name):
            return self.values.get(name)

    for path, function in ((package, '__anonymous'),
                           (recipes / 'iotbench-password-leak.inc', 'iotbench_password_leak_guard')):
        code = recipe_function(path, function)
        for mode, enabled, machine, variant in itertools.product(
                ('production', 'fixture'), ('0', '1'),
                LIB['MACHINES'] + ('hardware',), LIB['VARIANTS'] + ('unknown',)):
            data = Data(mode, enabled, machine, variant)
            action = lambda: exec(code, {'d': data, 'bb': BB})
            if mode == 'fixture' and enabled == '1' and machine in LIB['MACHINES'] and variant in LIB['VARIANTS']:
                action()
            else:
                rejected(action)
        if function != '__anonymous':
            data = Data('fixture', '1', 'qemuarm64', 'conf-password', extra=True)
            rejected(lambda: exec(code, {'d': data, 'bb': BB}))
    check('${FIXTURE_ROOT}' in package.read_text(), 'Missing package file boundary')
    passed(str(len(expected)) + ' image recipes, 15 package recipes and actual recipe guards (mock BitBake metadata)')


def native_tests(work):
    compiler = shutil.which('cc')
    check(compiler is not None, 'Native cc compiler required')
    for variant in ('c-password', 'header-password'):
        item = INVENTORY[variant]
        source = SOURCE / 'fixtures' / variant / item['file']
        directory = work / ('native-' + variant)
        directory.mkdir()
        driver = directory / 'driver.c'
        prefix = ('#include "' + str(source) + '"\n' if variant == 'header-password'
                  else 'int fixture_auth(const char *candidate);\n')
        driver.write_text(prefix + 'int main(int argc, char **argv) {\n'
                          '    return argc == 2 && fixture_auth(argv[1]) ? 0 : 1;\n}\n')
        for enabled in (False, True):
            binary = directory / ('enabled' if enabled else 'production')
            command = [compiler, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                       '-fstack-protector-strong', '-D_FORTIFY_SOURCE=2', '-fPIE', '-pie']
            if enabled:
                command.append('-DIOTBENCH_PASSWORD_LEAK_ENABLED=1')
            if variant == 'c-password':
                command.append(str(source))
            subprocess.run(command + [str(driver), '-o', str(binary)], check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            for candidate, expected_status in ((item['value'], 0 if enabled else 1), ('incorrect', 1)):
                result = subprocess.run([str(binary), candidate], stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, timeout=10)
                check(result.returncode == expected_status, 'Native auth routine mismatch')
            check((item['value'].encode() in binary.read_bytes()) == enabled,
                  'Production native stub retained synthetic credential')
    passed('C and header native authentication, wrong inputs and credential-free production stubs')


def wrapper_tests(work):
    directory = work / 'wrapper'
    directory.mkdir()
    environment = directory / 'bash-env'
    # Run the wrapper with a local environment hook, fake bitbake and an export
    # directory substitution. The opt-in and temporary-config code is unchanged.
    environment.write_text('source() { export BUILDDIR="$TEST_BUILD" MACHINE=qemuarm64; }\n'
                           'bitbake() { "$TEST_PYTHON" "$TEST_STUB" "$@"; }\n')
    stub = directory / 'bitbake.py'
    stub.write_text(textwrap.dedent('''\
        import json, os, pathlib, sys
        args = sys.argv[1:]
        config = pathlib.Path(args[1])
        assert args[0] == '-r'
        assert config.read_text() == ('IOTBENCH_BUILD_MODE = "fixture"\\n'
                                      'IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE = "1"\\n')
        pathlib.Path(os.environ['TEST_RECORD']).write_text(json.dumps(args))
        if os.environ.get('TEST_FAIL') == '1':
            sys.exit(42)
        image = args[2]
        deploy = pathlib.Path(os.environ['TEST_BUILD']) / 'tmp/deploy/images/qemuarm64'
        deploy.mkdir(parents=True, exist_ok=True)
        (deploy / (image + '-qemuarm64.rootfs.qemuboot.conf')).write_text('kernel_imagetype = Image\\n')
        (deploy / (image + '-qemuarm64.rootfs.ext4.zst')).write_bytes(b'stub image')
        (deploy / 'Image').write_bytes(b'stub kernel')
        '''))
    original = (ROOT / 'scripts/container-build-and-export.sh').read_text()
    script = directory / 'wrapper.sh'
    script.write_text(original.replace('EXPORT_DIR="/export/', 'EXPORT_DIR="' + str(directory / 'export') + '/'))
    env = os.environ.copy()
    for name in list(env):
        if name.startswith('IOTBENCH_'):
            del env[name]
    env.update(BASH_ENV=str(environment), TEST_BUILD=str(directory / 'build'),
               TEST_PYTHON=sys.executable, TEST_STUB=str(stub), TEST_RECORD=str(directory / 'record'),
               FIRMWARE='router-cwe798-password-leak-conf-password',
               IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE='1', IOTBENCH_BUILD_MODE='fixture')

    def run(overrides):
        current = dict(env, **overrides)
        return subprocess.run(['bash', str(script)], env=current, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=15)

    for fail in ('0', '1'):
        result = run({'TEST_FAIL': fail})
        check(result.returncode == (0 if fail == '0' else 42), 'Wrapper/stub failed: ' + result.stderr.decode())
        args = json.loads((directory / 'record').read_text())
        check(args[2] == 'iotbench-router-cwe798-password-leak-conf-password', 'Wrong firmware selected')
        check(not Path(args[1]).exists(), 'Temporary opt-in config persisted')
    for overrides in (
            {'IOTBENCH_BUILD_MODE': 'production'},
            {'FIRMWARE': 'router-cwe078-os-command-injection'},
            {'IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE': '1'},
            {'IOTBENCH_ENABLE_TELNET_FIXTURE': '1'},
            {'IOTBENCH_ENABLE_SUDO_ENV_FIXTURE': '1'},
            {'IOTBENCH_ENABLE_FTP_WRITE_FIXTURE': '1'}):
        (directory / 'record').unlink()
        check(run(overrides).returncode != 0 and not (directory / 'record').exists(),
              'Invalid wrapper context reached BitBake')
        (directory / 'record').write_text('[]')

    # Catalog default/opt-in behavior, with Docker replaced by a recording stub.
    bin_dir = directory / 'bin'
    bin_dir.mkdir()
    docker = bin_dir / 'docker'
    docker.write_text('#!/usr/bin/env python3\nimport json, os, sys\n'
                      'with open(os.environ["TEST_CATALOG"], "a") as stream:\n'
                      '    stream.write(json.dumps([os.environ["FIRMWARE"], sys.argv[1:]]) + "\\n")\n')
    docker.chmod(0o755)
    catalog = directory / 'catalog'
    for enabled in ('0', '1'):
        if catalog.exists():
            catalog.unlink()
        current = dict(env, PATH=str(bin_dir) + os.pathsep + env['PATH'], TEST_CATALOG=str(catalog),
                       IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE=enabled, MACHINES='qemuarm64')
        result = subprocess.run(['sh', str(ROOT / 'scripts/build-all.sh')], env=current,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        check(result.returncode == 0, 'Catalog failed')
        entries = [json.loads(line) for line in catalog.read_text().splitlines()]
        leak = [args for firmware, args in entries if '-cwe798-password-leak-' in firmware]
        check(len(leak) == (165 if enabled == '1' else 0), 'Wrong catalog opt-in coverage')
        check(all('IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE=1' in args
                  and 'IOTBENCH_BUILD_MODE=fixture' in args for args in leak),
              'Catalog dropped explicit fixture configuration')
    passed('wrapper rejects mixed/production opt-ins, cleans config on success/failure; catalog skips/enables 165 images (stubs)')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--isolated-fixture', action='store_true')
    parser.add_argument('--rootfs', type=Path, help='Validate an extracted, dedicated fixture rootfs')
    parser.add_argument('--variant', choices=LIB['VARIANTS'])
    args = parser.parse_args()
    if not args.isolated_fixture:
        parser.exit(77, 'Tests require --isolated-fixture\n')
    check(set(INVENTORY) == set(EXPECTED) == set(LIB['VARIANTS']), 'Inventory coverage mismatch')
    check(len({v['value'] for v in INVENTORY.values()}) == len(INVENTORY), 'Duplicate synthetic secret')
    check(all(LIB['SECRET'].fullmatch(v['value']) for v in INVENTORY.values()), 'Non-synthetic inventory value')
    if args.rootfs:
        if not args.variant:
            parser.error('--rootfs requires --variant')
        verify(args.rootfs.resolve(), args.variant)
        passed('extracted filesystem matches one expected synthetic credential')
        return
    with tempfile.TemporaryDirectory(prefix='iotbench-password-leak-') as temp:
        work = Path(temp)
        policy_tests(work)
        integration_tests()
        staged_tests(work)
        native_tests(work)
        wrapper_tests(work)
    print('PASS all ' + str(len(GROUPS)) + ' test groups')


if __name__ == '__main__':
    main()
