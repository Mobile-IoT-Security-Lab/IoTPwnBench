#!/usr/bin/env python3
"""Run only inside an explicitly opted-in disposable firmware guest."""
import ftplib
import io
import json
import os
from pathlib import Path
import pwd
import stat
import socket
import subprocess
import sys
import time

BASE = Path('/srv/iotbench-ftp')
MARKER = Path('/run/iotbench-ftp-write-test')
UNIT = 'iotbench-ftp-write.service'
PAYLOAD = b'ordinary synthetic FTP upload\n'


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def denied(operation, code='550'):
    try:
        operation()
    except ftplib.error_perm as error:
        assert str(error).startswith(code), str(error)
    else:
        raise AssertionError('Unauthorized operation unexpectedly succeeded')


def connect():
    ftp = ftplib.FTP(timeout=5)
    ftp.connect('127.0.0.1', 2121)
    return ftp


def client():
    assert MARKER.is_file()
    assert Path('/etc/iotbench/vsftpd-write-rights.conf').is_file()
    # This process must have entered the daemon's private network namespace.
    assert os.readlink('/proc/self/ns/net') != os.readlink('/proc/1/ns/net')
    deadline = time.monotonic() + 10
    while True:
        try:
            with socket.create_connection(('127.0.0.1', 2121), timeout=1):
                break
        except OSError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.1)
    for name, password in [('anonymous', 'test'), ('root', 'routeradmin'),
                           ('ftpfixture', 'wrong-password')]:
        with connect() as ftp:
            denied(lambda: ftp.login(name, password), '530')
    print('PASS authentication required; anonymous, root and wrong password rejected', flush=True)
    with connect() as ftp:
        ftp.login('ftpfixture', 'Fixture-FTP-Only-42')
        assert {'bad', 'control'} <= set(ftp.nlst())
        policy = json.loads(Path(__file__).with_name('policy.json').read_text())
        for directory in ('bad', 'control'):
            lines = []
            ftp.retrlines('LIST ' + directory, lines.append)
            for filename in policy['export_files']:
                assert any(filename in line for line in lines), filename
                data = io.BytesIO()
                ftp.retrbinary('RETR ' + directory + '/' + filename, data.write)
                content = data.getvalue()
                assert content, filename
                if filename == 'readme.txt':
                    assert b'Uploads are prohibited by policy.' in content
                elif filename == 'device.conf':
                    assert content == Path('/etc/iotbench/device.conf').read_bytes()
                elif filename == 'peripherals.conf':
                    assert content == Path('/etc/iotbench/peripherals.conf').read_bytes()
                elif filename == 'settings.json':
                    settings = json.loads(content)
                    assert all(key in settings for key in ('lan_ip', 'ssid', 'dhcp_start'))
        print('PASS directory listing and normal reads', flush=True)
        denied(lambda: ftp.storbinary('STOR control/probe.txt', io.BytesIO(PAYLOAD)), ('550', '553'))
        ftp.storbinary('STOR bad/probe.txt', io.BytesIO(PAYLOAD))
        data = io.BytesIO()
        ftp.retrbinary('RETR bad/probe.txt', data.write)
        assert data.getvalue() == PAYLOAD
        print('PASS discrepancy: read-only policy violated in bad; control rejects upload', flush=True)
        for path in ('/etc/passwd', '../etc/passwd', 'bad/../control/readme.txt'):
            denied(lambda: ftp.retrbinary('RETR ' + path, lambda data: None))
        print('PASS filesystem access contained', flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['--client']:
        client()
    else:
        if sys.argv[1:] != ['--isolated-fixture']:
            raise SystemExit('Requires --isolated-fixture in a disposable firmware guest')
        assert os.getuid() == 0
        assert Path('/etc/iotbench/vsftpd-write-rights.conf').is_file()
        assert not MARKER.exists(), 'Fixture already in use'
        assert subprocess.call(['systemctl', 'is-active', '--quiet', UNIT]) != 0
        policy = json.loads(Path(__file__).with_name('policy.json').read_text())
        assert 'STOR' in policy['prohibited_operations']
        account = pwd.getpwnam(policy['user'])
        assert account.pw_uid != 0 and account.pw_shell == '/bin/false'
        modes = {p: stat.S_IMODE(p.stat().st_mode) for p in (BASE / 'bad', BASE / 'control')}
        for name, expected in policy['directories'].items():
            assert modes[BASE / name] == int(expected['fixture_mode'], 8)
        assert policy['directories']['bad']['intended_mode'] == '0755'
        for p in modes:
            assert p.stat().st_uid == 0 and p.stat().st_gid == account.pw_gid
            assert not (p / 'probe.txt').exists()
        try:
            MARKER.write_text('explicit disposable guest test\n')
            subprocess.check_call(['systemctl', 'start', UNIT])
            pid = run('systemctl', 'show', '--property=MainPID', '--value', UNIT)
            assert int(pid) > 0
            assert os.readlink('/proc/' + pid + '/ns/net') != os.readlink('/proc/1/ns/net')
            # Wait for listener without contacting any host or external network.
            subprocess.check_call(['nsenter', '-t', pid, '-n', sys.executable,
                                   __file__, '--client'])
            uploaded = BASE / 'bad/probe.txt'
            assert uploaded.stat().st_uid == account.pw_uid, 'FTP upload executed with wrong identity'
            assert not (BASE / 'control/probe.txt').exists()
            # Repair the sole defect, then prove the formerly writable path rejects STOR.
            (BASE / 'bad').chmod(0o755)
            check = "import ftplib,io; f=ftplib.FTP(); f.connect('127.0.0.1',2121); f.login('ftpfixture','Fixture-FTP-Only-42');\ntry: f.storbinary('STOR bad/repaired.txt',io.BytesIO(b'test'))\nexcept ftplib.error_perm as e: assert str(e).startswith(('550', '553'))\nelse: raise AssertionError('Repair did not enforce policy')\nf.quit()"
            subprocess.check_call(['nsenter', '-t', pid, '-n', sys.executable, '-c', check])
            print('PASS static permissions, unprivileged upload ownership and repaired-directory control', flush=True)
        finally:
            subprocess.call(['systemctl', 'stop', UNIT])
            for directory in ('bad', 'control'):
                for name in ('probe.txt', 'repaired.txt'):
                    (BASE / directory / name).unlink(missing_ok=True)
            for path, mode in modes.items():
                path.chmod(mode)
            MARKER.unlink(missing_ok=True)
