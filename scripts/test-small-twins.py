#!/usr/bin/env python3
"""Offline checks of the corrected REST, cron wildcard, sudo environment and Telnet twins."""

import argparse
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile

os.umask(0o022)
ROOT = Path(__file__).resolve().parents[1]
VULNS = ROOT / 'meta-iotbench/recipes-vulns'


def overlay(module, work):
    source = work / module
    shutil.copytree(VULNS / module / 'files', source)
    shutil.copytree(VULNS / module / 'files-fixed', source, dirs_exist_ok=True)
    return source


def cron(work):
    source = overlay('cwe088-cronjob-wildcard-injection', work)
    build = runpy.run_path(str(source / 'fixture-build.py'))
    binary = work / 'fixture-maintenance'
    subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-DIOTBENCH_CRON_WILDCARD_FIXTURE_ENABLED=1',
                    '-DFIXTURE_ROOT="' + str(work / 'cron-out/usr/share/iotbench/cronjob-wildcard-injection') + '"',
                    str(source / 'fixture-maintenance.c'), '-o', str(binary)], check=True)
    root = build['stage'](work / 'cron-out', 'fixture', '1', 'qemuarm64', binary, False)
    assert b'--fixture-test *' not in (root / 'cron/vulnerable.crontab').read_bytes()
    assert b'--fixture-test -- *' in (root / 'cron/secure.crontab').read_bytes()
    (root / 'inbox/--fixture-diagnostic').write_text('x')
    result = subprocess.run([sys.executable, str(root / 'fixture-runner.py'), '--isolated-fixture'],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    events = [json.loads(line) for line in result.stdout.splitlines()]
    assert events[-1]['result'] == 'nominal' and events[-1]['options'] == 0, events
    print('PASS corrected cron twin: a --fixture-diagnostic file name stays an operand, result nominal')


def sudo(work):
    source = overlay('cwe798-sudo-environment', work)
    policy = (source / 'iotbench-sudo-environment').read_text()
    vulnerable = (VULNS / 'cwe798-sudo-environment/files/iotbench-sudo-environment').read_text()
    assert 'env_keep' in vulnerable, 'The vulnerable policy should preserve POSIXLY_CORRECT'
    assert 'env_keep' not in policy and 'env_reset' in policy and '!setenv' in policy
    assert not (source / 'fixture-sudo-env.c').exists() and not (source / 'test-session.py').exists()
    print('PASS corrected sudo twin: env_reset and no env_keep, so POSIXLY_CORRECT no longer changes the report units')


def telnet(work):
    source = overlay('cwe798-unencrypted-traffic', work)
    build = runpy.run_path(str(source / 'fixture-build.py'))
    build['stage'](work / 'telnet-out', 'fixture', '1', 'qemuarm64', True)
    tree = {p.relative_to(work / 'telnet-out').as_posix() for p in (work / 'telnet-out').rglob('*') if p.is_file()}
    assert not any('telnet.service' in name for name in tree), tree
    assert 'password' not in json.loads((source / 'ground-truth.json').read_text())
    print('PASS corrected Telnet twin: no cleartext service unit and no public password')


def rest(work):
    source = overlay('cwe022-rest-internal-files', work)
    recipe = (VULNS / 'cwe022-rest-internal-files/cwe022-rest-internal-files-fixed_1.0.bb').read_text()
    assert recipe.count('-DREST_SECURE_CONTROL=1') == 2 and '-DREST_SECURE_CONTROL=0' not in recipe
    truth = json.loads((source / 'ground-truth.json').read_text())
    assert truth['intentional_vulnerabilities'] == 0 and truth['boundary']['status'] == 403
    print('PASS corrected REST twin: both binaries are built with the traversal control enabled')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--isolated-fixture', action='store_true', required=True)
    parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='small-twins-') as temp:
        work = Path(temp)
        for check in (rest, cron, sudo, telnet):
            check(work)
    return 0


if __name__ == '__main__':
    sys.exit(main())
