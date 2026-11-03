#!/usr/bin/env python3
"""Copy only public runtime code into a disposable root; never bind host directories."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile

HERE = Path(__file__).resolve().parent
CWES = ('089', '079', '020', '352', '078', '022', '077', '306', '862', '287')
DEVICES = ('router', 'ipcamera', 'smartplug', 'thermostat', 'plc', 'smartbulb',
           'smarthub', 'envsensor', 'smartspeaker', 'healthmonitor', 'doorlock')
MODULES = ('mpm_prefork', 'authz_core', 'unixd', 'alias', 'cgi')


def validate_build(mode, enable, machine):
    if mode != 'fixture' or enable != '1' or machine not in ('qemuarm64', 'qemuarm', 'qemux86-64', 'qemux86', 'qemumips'):
        raise ValueError('Apache fixtures require fixture mode, explicit enable=1 and a QEMU machine')


def installed_variant():
    path = HERE / 'variant.json'
    return json.loads(path.read_text())['cwe'] if path.exists() else None


def stage(root, cwe, apache, modules, browser=None):
    root = Path(root)
    root.mkdir(mode=0o755)
    for name in ('oldroot', 'proc', 'state', 'tmp', 'run', 'dev/shm', 'fixture', 'modules', 'empty', 'attacker', 'etc'):
        (root / name).mkdir(parents=True, exist_ok=True)
    for device in ('null', 'zero', 'random', 'urandom'):
        (root / 'dev' / device).touch()
    (root / 'etc/passwd').write_text('fixture:x:1000:1000:Synthetic fixture:/tmp:/bin/sh\n')
    (root / 'etc/group').write_text('fixture:x:1000:\n')
    (root / 'etc/nsswitch.conf').write_text('passwd: files\ngroup: files\nhosts: files\n')
    (root / 'etc/hosts').write_text('127.0.0.1 localhost\n')
    copied = set()

    def copy(path, destination=None):
        path = Path(path)
        target = root / (destination or str(path).lstrip('/'))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(path), str(target))
        target.chmod(0o755 if os.access(str(path), os.X_OK) else 0o644)
        return target

    def binary(path, destination=None):
        path = Path(path)
        key = (str(path), destination)
        if key in copied:
            return
        copied.add(key)
        copy(path, destination)
        output = subprocess.check_output(['ldd', str(path)], universal_newlines=True)
        for line in output.splitlines():
            if 'not found' in line:
                raise RuntimeError('Missing runtime library: ' + line)
            match = re.search(r'(?:=>\s*)?(/[^\s]+)', line)
            if match:
                lib = match.group(1)
                if (lib, None) not in copied:
                    copied.add((lib, None))
                    copy(lib)

    binary(apache, 'usr/sbin/httpd')
    binary(sys.executable, 'usr/bin/python3')
    binary('/bin/sh')
    for library in Path('/lib').glob('**/libnss_files.so.2'):
        binary(library)
    builtin = subprocess.check_output([apache, '-l'], universal_newlines=True)
    for module in MODULES:
        if 'mod_' + module + '.c' not in builtin:
            binary(Path(modules) / ('mod_' + module + '.so'), 'modules/mod_' + module + '.so')
    stdlib = Path(sysconfig.get_path('stdlib'))
    destination = root / str(stdlib).lstrip('/')
    shutil.copytree(str(stdlib), str(destination), ignore=shutil.ignore_patterns(
        'site-packages', 'dist-packages', '__pycache__', 'test', 'tests', 'ensurepip', 'idlelib', 'tkinter'))
    # Resolve shared libraries used by Python extension modules (including SQLite).
    for extension in stdlib.glob('lib-dynload/*.so'):
        binary(extension)
    # Debian keeps extension modules in a separate multiarch directory on some releases.
    for extension in destination.rglob('*.so'):
        original = Path('/') / extension.relative_to(root)
        binary(original)
    for name in ('app.cgi', 'httpd.conf.in', 'test-fixtures.py', 'browser.py'):
        copy(HERE / name, 'fixture/' + name)
    config = root / 'fixture/httpd.conf.in'
    config.write_text(''.join(line for line in config.read_text().splitlines(True)
                             if not (line.startswith('LoadModule ') and
                                     'mod_' + line.split()[1].removesuffix('_module') + '.c' in builtin)))
    scenario = HERE / 'variants' / ('cwe' + cwe + '.py')
    if not scenario.exists():
        if installed_variant() != cwe:
            raise ValueError('This image contains a different fixture variant')
        scenario = HERE / 'scenario.py'
    copy(scenario, 'fixture/scenario.py')
    (root / 'fixture/app.cgi').chmod(0o755)
    (root / 'fixture/variant.json').write_text(json.dumps({'cwe': cwe}))
    (root / 'attacker/index.html').write_text('''<!doctype html><title>Local CSRF origin</title>
<form id="attack" method="POST" action="http://127.0.0.1:18080/app/setting">
<input name="value" value="csrf-marker"><button>Submit synthetic change</button></form>''')
    if browser:
        browser = Path(browser).resolve()
        fonts = sorted(Path('/usr/share/fonts').rglob('*.ttf'))
        if not fonts:
            raise RuntimeError('Browser tests require an installed TrueType font')
        copy(fonts[0], 'fonts/fixture.ttf')
        (root / 'etc/fonts').mkdir()
        (root / 'etc/fonts/fonts.conf').write_text(
            '<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd">'
            '<fontconfig><dir>/fonts</dir><cachedir>/tmp/font-cache</cachedir></fontconfig>')
        shutil.copytree(str(browser.parent), str(root / 'browser'),
                        ignore=shutil.ignore_patterns('chrome-sandbox', '*crash*.dmp', 'libqt5_shim.so', 'libqt6_shim.so', browser.name))
        # Chrome and Chromium distributions use different executable names.
        binary(browser, 'browser/chrome')
        for path in browser.parent.iterdir():
            # Qt GUI integrations are optional and unused by headless Chrome.
            if path == browser or path.name in ('libqt5_shim.so', 'libqt6_shim.so'):
                continue
            if path.is_file() and (path.name in ('chrome', 'chrome_crashpad_handler') or path.suffix == '.so'):
                binary(path, 'browser/' + path.name)
        (root / 'fixture/browser-enabled').touch()
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', default='production')
    parser.add_argument('--enable', default='0')
    parser.add_argument('--machine', default='qemuarm64')
    parser.add_argument('--cwe', choices=CWES, required=True)
    parser.add_argument('--apache', default=shutil.which('apache2') or shutil.which('httpd') or '/usr/sbin/apache2')
    parser.add_argument('--modules', default='/usr/lib/apache2/modules')
    parser.add_argument('--browser', type=Path)
    parser.add_argument('--http-only', action='store_true', help='Explicit partial run; omits browser evidence')
    args = parser.parse_args()
    if sys.version_info < (3, 9):
        parser.error('Python 3.9 or newer is required')
    try:
        validate_build(args.mode, args.enable, args.machine)
    except ValueError as error:
        parser.error(str(error))
    if installed_variant() and installed_variant() != args.cwe:
        parser.error('The installed fixture contains only CWE-' + installed_variant())
    if args.cwe in ('079', '352') and not args.browser and not args.http_only:
        parser.error('XSS/CSRF require --browser PATH; --http-only explicitly runs partial validation')
    if os.geteuid() == 0:
        parser.error('Run as an ordinary unprivileged user')
    with tempfile.TemporaryDirectory(prefix='iotbench-apache-') as temporary:
        base = Path(temporary)
        isolate = HERE / 'isolate'
        if not isolate.exists():
            isolate = base / 'isolate'
            subprocess.run(['cc', '-std=c11', '-O2', '-D_FORTIFY_SOURCE=2', '-fstack-protector-strong',
                            '-Wall', '-Wextra', '-Werror', '-Wl,-z,relro,-z,now', str(HERE / 'isolate.c'),
                            '-o', str(isolate)], check=True)
        root = stage(base / 'root', args.cwe, args.apache, args.modules,
                     args.browser if args.cwe in ('079', '352') else None)
        subprocess.run([str(isolate), '--isolated-fixture', str(root), '/usr/bin/python3',
                        '/fixture/test-fixtures.py'], check=True, timeout=1800)


if __name__ == '__main__':
    main()
