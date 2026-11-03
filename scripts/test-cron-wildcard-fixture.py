#!/usr/bin/env python3
"""Offline native fixture regression tests; no daemon, shell commands or network."""

import argparse
import json
import os
from pathlib import Path
import re
import runpy
import stat
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / 'meta-iotbench'
SLUG = 'cwe088-cronjob-wildcard-injection'
SOURCE = LAYER / 'recipes-vulns' / SLUG / 'files'
BUILD = runpy.run_path(str(SOURCE / 'fixture-build.py'))
RUNNER = runpy.run_path(str(SOURCE / 'fixture-runner.py'))


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='iotbench-cron-fixture-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        # Exercise quoting in staged crontabs and literal argv paths.
        self.root = BUILD['stage'](self.base / 'stage with spaces', 'fixture', '1', 'qemuarm64')
        self.inbox = self.root / 'inbox'
        self.helper = self.root / 'bin/fixture-maintenance'

    def run_schedule(self, secure=False):
        log = self.root / 'logs' / ('secure.jsonl' if secure else 'vulnerable.jsonl')
        if log.exists():
            log.unlink()
        events = RUNNER['run_once'](self.root, secure)
        self.assertEqual(events, [json.loads(line) for line in log.read_text().splitlines()])
        self.assertEqual(stat.S_IMODE(log.stat().st_mode), 0o600)
        self.assertEqual(events[0], {'context': 'root-cron-maintenance',
                                     'cron_runas': 'root', 'helper_changes_uid': False})
        return events

    def invoke(self, args, cwd=None):
        return subprocess.run([str(self.helper)] + args, cwd=str(cwd or self.inbox),
                              stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True, timeout=10)

    def test_ordinary_and_option_filename_secure_control(self):
        normal = self.run_schedule()
        self.assertEqual(normal[-1], {'options': 0, 'operands': 2, 'result': 'nominal'})
        self.assertEqual([e['argument'] for e in normal if e.get('kind') == 'operand'],
                         ['alpha.record', 'beta.record'])
        boundary = self.inbox / '--fixture-diagnostic'
        boundary.write_text('harmless option-like filename\n')
        vulnerable = self.run_schedule()
        self.assertIn({'kind': 'option', 'argument': boundary.name}, vulnerable)
        self.assertEqual(vulnerable[-1], {'options': 1, 'operands': 2,
                                         'result': 'synthetic-diagnostic'})
        secure = self.run_schedule(secure=True)
        self.assertIn({'kind': 'operand', 'argument': boundary.name}, secure)
        self.assertEqual(secure[-1], {'options': 0, 'operands': 3, 'result': 'nominal'})
        boundary.rename(self.inbox / 'renamed.record')
        self.assertEqual(self.run_schedule()[-1]['result'], 'nominal')

    def test_separator_unknown_options_and_option_after_ordinary_operand(self):
        # Parsing continues after ordinary operands until --, as many tools do.
        result = self.invoke(['--fixture-test', 'alpha.record', '--fixture-diagnostic'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout.splitlines()[-1])['result'], 'synthetic-diagnostic')
        for name in ('--unknown', '-q', '-'):
            (self.inbox / name).touch()
        result = self.run_schedule()
        self.assertEqual(result[-1], {'options': 2, 'operands': 3, 'result': 'nominal'})
        (self.inbox / '--').touch()
        (self.inbox / '--fixture-diagnostic').touch()
        result = self.run_schedule()
        self.assertEqual(result[-1], {'options': 0, 'operands': 6, 'result': 'nominal'})
        self.assertIn({'kind': 'separator'}, result)

    def test_only_inbox_names_influence_arguments_and_no_operand_access(self):
        baseline = self.run_schedule()[-1]
        # Sibling directories and hidden names do not enter bare * expansion.
        for directory in (self.root, self.root / 'logs', self.base):
            (directory / '--fixture-diagnostic').touch()
        (self.inbox / '.--fixture-diagnostic').touch()
        (self.inbox / 'nested').mkdir()
        (self.inbox / 'nested/--fixture-diagnostic').touch()
        result = self.run_schedule()
        self.assertEqual(result[-1], dict(baseline, operands=3))
        canary = self.base / 'synthetic-private-canary'
        canary.write_text('FAKE-PRIVATE-DATA-DO-NOT-READ\n')
        canary.chmod(0o400)
        (self.inbox / 'linked.record').symlink_to(canary)
        (self.inbox / 'unreadable.record').touch(mode=0o000)
        result = self.run_schedule()
        self.assertEqual(result[-1]['result'], 'nominal')
        self.assertNotIn('FAKE-PRIVATE-DATA', json.dumps(result))
        self.assertEqual(canary.read_text(), 'FAKE-PRIVATE-DATA-DO-NOT-READ\n')
        self.assertEqual(stat.S_IMODE(canary.stat().st_mode), 0o400)

    def test_filename_metacharacters_are_literal_data(self):
        names = ['$(touch SHOULD_NOT_EXIST)', '`touch SHOULD_NOT_EXIST`',
                 'semi;touch SHOULD_NOT_EXIST', 'space name', 'quote"name',
                 'line\nbreak', '--fixture-diagnostic;touch SHOULD_NOT_EXIST']
        for name in names:
            (self.inbox / name).touch()
        result = self.run_schedule()
        self.assertEqual(set(names).difference(e.get('argument') for e in result), set())
        self.assertEqual(result[-1]['result'], 'nominal')
        self.assertFalse((self.inbox / 'SHOULD_NOT_EXIST').exists())
        self.assertEqual(self.run_schedule(True)[-1]['options'], 0)

    def test_empty_inbox_matches_unmatched_shell_glob(self):
        for path in self.inbox.iterdir():
            path.unlink()
        events = self.run_schedule()
        self.assertIn({'kind': 'operand', 'argument': '*'}, events)
        self.assertEqual(events[-1], {'options': 0, 'operands': 1, 'result': 'nominal'})

    def test_helper_requires_compiled_fixture_manifest_and_cwd(self):
        self.assertEqual(self.invoke([]).returncode, 77)
        self.assertEqual(self.invoke(['--fixture-test'], self.root).returncode, 77)
        marker = self.root / 'build-config'
        original = marker.read_bytes()
        marker.write_text('production\n')
        self.assertEqual(self.invoke(['--fixture-test']).returncode, 77)
        marker.write_bytes(original)
        marker.chmod(0o666)
        self.assertEqual(self.invoke(['--fixture-test']).returncode, 77)
        marker.chmod(0o644)
        copy = self.root / 'marker-copy'
        marker.rename(copy)
        marker.symlink_to(copy)
        self.assertEqual(self.invoke(['--fixture-test']).returncode, 77)
        production = self.base / 'production-helper'
        for flags in ([], ['-DIOTBENCH_CRON_WILDCARD_FIXTURE_ENABLED=0']):
            subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror'] + flags +
                           [str(SOURCE / 'fixture-maintenance.c'), '-o', str(production)], check=True)
            result = subprocess.run([str(production), '--fixture-test', '--fixture-diagnostic'],
                                    cwd=str(self.inbox), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    universal_newlines=True, timeout=10)
            self.assertEqual(result.returncode, 77)
            self.assertEqual(result.stdout, '')
            self.assertNotIn(b'synthetic-diagnostic', production.read_bytes())

    def test_public_cli_requires_explicit_test_configuration(self):
        runner = self.root / 'fixture-runner.py'
        result = subprocess.run(['python3', str(runner), '--root', str(self.root)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(list((self.root / 'logs').iterdir()), [])
        result = subprocess.run(['python3', str(runner), '--root', str(self.root),
                                 '--isolated-fixture'], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, universal_newlines=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout.splitlines()[-1]),
                         {'options': 0, 'operands': 2, 'result': 'nominal'})
        disabled = self.base / 'cli-production'
        result = subprocess.run(['python3', str(ROOT / 'scripts/build-cron-wildcard-fixture.py'),
                                 '--output', str(disabled)], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(disabled.exists())

    def test_runner_rejects_config_changes_symlinks_and_existing_logs(self):
        config = self.root / 'cron/vulnerable.crontab'
        original = config.read_text()
        for modified in (original.replace('*/5', '*'), original.replace(' root ', ' nobody '),
                         original.replace(' *\n', ' ../*\n'),
                         original + '0 * * * * root /bin/false\n',
                         original.replace(' *\n', ' *; touch SHOULD_NOT_EXIST\n')):
            config.write_text(modified)
            with self.assertRaises(ValueError):
                RUNNER['run_once'](self.root)
        config.write_text(original)
        self.inbox.rename(self.root / 'saved-inbox')
        self.inbox.symlink_to(self.root / 'saved-inbox', target_is_directory=True)
        with self.assertRaises(ValueError):
            RUNNER['run_once'](self.root)
        self.inbox.unlink()
        (self.root / 'saved-inbox').rename(self.inbox)
        log = self.root / 'logs/vulnerable.jsonl'
        canary = self.base / 'log-canary'
        canary.write_text('unchanged')
        log.symlink_to(canary)
        with self.assertRaises(OSError):
            RUNNER['run_once'](self.root)
        self.assertEqual(canary.read_text(), 'unchanged')
        log.unlink()
        log.write_text('existing log')
        with self.assertRaises(OSError):
            RUNNER['run_once'](self.root)
        self.assertEqual(log.read_text(), 'existing log')
        config.chmod(0o666)
        with self.assertRaises(ValueError):
            RUNNER['run_once'](self.root)

    def test_source_binary_and_staged_tree_safeguards(self):
        source = (SOURCE / 'fixture-maintenance.c').read_text()
        forbidden = r'\b(system|popen|exec\w*|posix_spawn\w*|socket|connect|bind|listen|set\w*uid|set\w*gid|chmod|chown|unlink|rename|fopen|fwrite)\s*\('
        self.assertIsNone(re.search(forbidden, source))
        self.assertEqual(re.findall(r'\bopen\(([^,]+),', source), ['FIXTURE_ROOT "/build-config"'])
        imports = subprocess.check_output(['nm', '-u', str(self.helper)], universal_newlines=True)
        self.assertIsNone(re.search(r'\b(system|popen|exec\w*|posix_spawn\w*|socket|setuid|setgid)@', imports))
        for path in (self.base / 'stage with spaces').rglob('*'):
            self.assertEqual(path.stat().st_mode & 0o6022, 0, str(path))
        self.assertFalse((self.base / 'stage with spaces/etc').exists())
        self.assertEqual(stat.S_IMODE(self.inbox.stat().st_mode), 0o750)
        self.assertEqual(stat.S_IMODE(self.helper.stat().st_mode), 0o755)

    def test_device_integration_and_actual_recipe_build_guards(self):
        devices = sorted(path.parent.name for path in (LAYER / 'recipes-devices').glob('*/device-*.inc'))
        images = LAYER / 'recipes-images'
        actual = sorted(path.name[len('iotbench-'):-len('-' + SLUG + '.bb')]
                        for path in images.glob('iotbench-*-' + SLUG + '.bb'))
        self.assertEqual(actual, devices)
        for device in devices:
            recipe = (images / ('iotbench-' + device + '-' + SLUG + '.bb')).read_text()
            self.assertEqual(re.findall(r'^require (.+)$', recipe, re.M), [
                'recipes-images/iotbench-image.inc',
                'recipes-devices/{0}/device-{0}.inc'.format(device),
                'recipes-images/iotbench-cronjob-wildcard-injection.inc'])
        common = images / 'iotbench-cronjob-wildcard-injection.inc'
        self.assertIn('IOTBENCH_VULN_INSTALL = "' + SLUG + '"', common.read_text())
        package = LAYER / 'recipes-vulns' / SLUG / (SLUG + '_1.0.bb')
        recipe = package.read_text()
        for expected in ('--shell /bin/false --password', '--uid 988', '--gid 988',
                         'chown fixturefiles:fixturefiles', 'FILES:${PN} = "${FIXTURE_ROOT}"',
                         'do_compile[vardeps]', 'do_install[vardeps]', '--target-paths'):
            self.assertIn(expected, recipe)
        truth = json.loads((SOURCE / 'ground-truth.json').read_text())
        self.assertEqual(truth['catalog_cwe'], 'CWE-88')
        self.assertEqual(truth['related_cwes'], ['CWE-78', 'CWE-269'])
        self.assertTrue(truth['single_scenario'])

        def recipe_python(path, name):
            return textwrap.dedent(path.read_text().split('python ' + name + '() {\n', 1)[1]
                                   .split('\n}', 1)[0])

        class BB:
            class parse:
                SkipRecipe = ValueError

                @staticmethod
                def mark_dependency(data, path):
                    assert Path(path).is_file()

            @staticmethod
            def fatal(message):
                raise ValueError(message)

        class Metadata:
            def __init__(self, mode, enabled, machine):
                self.values = {'IOTBENCH_BUILD_MODE': mode,
                               'IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE': enabled,
                               'MACHINE': machine, 'THISDIR': str(SOURCE.parent),
                               'IOTBENCH_CRON_FIXTURE_LAYER': str(LAYER)}

            def getVar(self, key):
                return self.values.get(key)

        guards = [recipe_python(package, '__anonymous'),
                  recipe_python(common, 'iotbench_cron_wildcard_fixture_guard')]
        for mode in ('production', 'fixture', None):
            for enabled in ('0', '1', None):
                for machine in BUILD['MACHINES'] + ('production-board', None):
                    valid = mode == 'fixture' and enabled == '1' and machine in BUILD['MACHINES']
                    data = Metadata(mode, enabled, machine)
                    for code in guards:
                        if valid:
                            exec(code, {'d': data, 'bb': BB})
                        else:
                            with self.assertRaises(ValueError):
                                exec(code, {'d': data, 'bb': BB})
                    if not valid:
                        output = self.base / 'forbidden-stage'
                        with self.assertRaises(ValueError):
                            BUILD['stage'](output, mode, enabled, machine)
                        self.assertFalse(output.exists())
        staged = BUILD['stage'](self.base / 'target-stage', 'fixture', '1', 'qemuarm',
                                binary=self.helper, target_paths=True)
        config = (staged / 'cron/vulnerable.crontab').read_text()
        self.assertIn('cd /usr/share/iotbench/cronjob-wildcard-injection/inbox && ', config)
        self.assertNotIn(str(self.base), config)

    def test_build_wrappers_default_exclusion_and_opt_in(self):
        fakebin = self.base / 'fakebin'
        fakebin.mkdir()
        logfile = self.base / 'calls'
        docker = fakebin / 'docker'
        docker.write_text('#!/bin/sh\nprintf "%s|%s\\n" "$FIRMWARE" "$*" >> "$FIXTURE_CALLS"\n')
        docker.chmod(0o755)
        env = {key: value for key, value in os.environ.items() if not key.startswith('IOTBENCH_')}
        env.update(PATH=str(fakebin) + ':' + os.environ['PATH'], FIXTURE_CALLS=str(logfile),
                   MACHINES='qemuarm64')
        def catalog(extra):
            logfile.write_text('')
            subprocess.run(['sh', str(ROOT / 'scripts/build-all.sh')], env=dict(env, **extra),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=30)
            return [line for line in logfile.read_text().splitlines() if SLUG in line]
        self.assertEqual(catalog({}), [])
        selected = catalog({'IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE': '1'})
        self.assertEqual(len(selected), 11)
        self.assertTrue(all('-e IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE=1' in call and
                            '-e IOTBENCH_BUILD_MODE=fixture' in call for call in selected))

        # Substitute only the unavailable container bootstrap. A stub BitBake
        # records its exact config, then exits before any export operation.
        wrapper = (ROOT / 'scripts/container-build-and-export.sh').read_text()
        bootstrap = self.base / 'bootstrap.sh'
        bootstrap.write_text(':\n')
        wrapper = wrapper.replace('source /opt/yocto/yocto-env.sh',
                                  'source ' + str(bootstrap))
        harness = self.base / 'container-wrapper.sh'
        harness.write_text(wrapper)
        bitbake = fakebin / 'bitbake'
        bitbake.write_text('#!/usr/bin/env python3\nimport json, os, pathlib, sys\n'
                           'args = sys.argv[1:]\n'
                           'conf = pathlib.Path(args[1]) if args[0] == "-r" else None\n'
                           'pathlib.Path(os.environ["FIXTURE_CALLS"]).write_text(json.dumps('
                           '{"args": args, "config": conf.read_text() if conf else None}))\n'
                           'sys.exit(39)\n')
        bitbake.chmod(0o755)
        fixture = {'FIRMWARE': 'router-' + SLUG, 'IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE': '1'}
        result = subprocess.run(['bash', str(harness)], env=dict(env, **fixture),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        self.assertEqual(result.returncode, 39, result.stderr)
        recorded = json.loads(logfile.read_text())
        self.assertEqual(recorded['config'], 'IOTBENCH_BUILD_MODE = "fixture"\n'
                         'IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE = "1"\n')
        self.assertEqual(recorded['args'][-1], 'iotbench-router-' + SLUG)
        self.assertFalse(Path(recorded['args'][1]).exists(), 'Temporary config not cleaned up')
        invalid = [{'IOTBENCH_BUILD_MODE': 'production'}, {'FIRMWARE': 'router-cwe190-integer-overflow'}]
        invalid += [{flag: '1'} for flag in ('IOTBENCH_ENABLE_SUDO_ENV_FIXTURE',
                                            'IOTBENCH_ENABLE_TELNET_FIXTURE',
                                            'IOTBENCH_ENABLE_FTP_WRITE_FIXTURE')]
        for overrides in invalid:
            values = dict(fixture, **overrides)
            logfile.write_text('not called')
            result = subprocess.run(['bash', str(harness)], env=dict(env, **values),
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(logfile.read_text(), 'not called')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--isolated-fixture', action='store_true', required=True)
    parser.parse_args()
    unittest.main(argv=[__file__], verbosity=2)
