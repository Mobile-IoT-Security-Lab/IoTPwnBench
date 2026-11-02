#!/usr/bin/env python3
"""Offline integration checks; never start FTP or change host accounts/permissions."""
import ast
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / 'meta-iotbench'
PACKAGE = LAYER / 'recipes-vulns/cwe276-bad-write-rights'
FILES = PACKAGE / 'files'


def check():
    devices = {p.name for p in (LAYER / 'recipes-devices').iterdir() if p.is_dir()}
    recipes = list((LAYER / 'recipes-images').glob('iotbench-*-cwe276-bad-write-rights.bb'))
    assert len(recipes) == len(devices) == 11
    for device in devices:
        recipe = LAYER / f'recipes-images/iotbench-{device}-cwe276-bad-write-rights.bb'
        text = recipe.read_text()
        assert f'require recipes-devices/{device}/device-{device}.inc' in text
        assert 'require recipes-images/iotbench-bad-write-rights.inc' in text
        assert 'IOTBENCH_VULN_INSTALL = "cwe276-bad-write-rights"' in text
    config = dict(line.split('=', 1) for line in (FILES / 'vsftpd.conf').read_text().splitlines()
                  if line and not line.startswith('#'))
    for key, value in {'listen_address': '127.0.0.1', 'anonymous_enable': 'NO',
                       'local_enable': 'YES', 'write_enable': 'YES',
                       'chroot_local_user': 'YES', 'allow_writeable_chroot': 'NO',
                       'userlist_deny': 'NO', 'port_enable': 'NO'}.items():
        assert config[key] == value, (key, config.get(key))
    assert config['deny_file'] == '..'
    assert config['local_root'] == '/srv/iotbench-ftp'
    assert (FILES / 'ftp-users').read_text() == 'ftpfixture\n'
    assert 'SITE' not in config['cmds_allowed'].split(',')
    policy = json.loads((FILES / 'policy.json').read_text())
    assert policy['directories']['bad']['fixture_mode'] != policy['directories']['bad']['intended_mode']
    assert policy['directories']['control']['fixture_mode'] == policy['directories']['control']['intended_mode']
    assert 'STOR' in policy['prohibited_operations']
    assert policy['export_files'] == ['readme.txt', 'device.conf', 'peripherals.conf', 'settings.json']
    recipe = (PACKAGE / 'cwe276-bad-write-rights_1.0.bb').read_text()
    for filename in re.findall(r'file://([^; "\n]+)', recipe):
        assert (FILES / filename).is_file(), filename
    assert 'install -d -m 0775 ${D}/srv/iotbench-ftp/bad' in recipe
    assert 'install -d -m 0755 ${D}/srv/iotbench-ftp ${D}/srv/iotbench-ftp/control' in recipe
    assert 'chown root:ftpfixture' in recipe
    assert '--shell /bin/false' in recipe
    unit = (FILES / 'iotbench-ftp-write.service').read_text()
    assert 'PrivateNetwork=yes' in unit and '[Install]' not in unit
    assert 'ConditionPathExists=/run/iotbench-ftp-write-test' in unit
    guard = (LAYER / 'recipes-images/iotbench-bad-write-rights.inc').read_text()
    assert 'IOTBENCH_ENABLE_FTP_WRITE_FIXTURE ?= "0"' in guard
    assert 'bb.fatal' in guard and '/dev/null' in guard
    assert 'iotbench_ftp_fixture_exports;' in guard
    for filename in ('device.conf', 'peripherals.conf', 'settings.json'):
        assert f'/srv/iotbench-ftp/$ftp_fixture_directory/{filename}' in guard, filename
    ast.parse((FILES / 'test-guest.py').read_text())
    ast.parse((ROOT / 'scripts/test-ftp-write-rights.py').read_text())
    print('PASS eleven image integrations, fixture assets, authentication, namespace and build gates')
    print('PASS static finding CWE-276: root:ftpfixture bad/ 0775 contradicts read-only policy; control/ 0755')


if __name__ == '__main__':
    check()
