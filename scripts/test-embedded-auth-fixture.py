#!/usr/bin/env python3
"""Offline deterministic artifact and Unix-socket regression. Explicit lab opt-in only."""

import argparse
import base64
import ctypes
import itertools
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import textwrap

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / 'meta-iotbench'
SOURCE = LAYER / 'recipes-vulns/cwe798-embedded-auth/files'
LIB = runpy.run_path(str(SOURCE / 'fixture-lib.py'))
BUILD = runpy.run_path(str(SOURCE / 'fixture-build.py'))
VERIFY = runpy.run_path(str(SOURCE / 'fixture-verify.py'))['verify']
RUNTIME = runpy.run_path(str(SOURCE / 'fixture-test.py'))
INVENTORY = json.loads((SOURCE / 'inventory.json').read_text())
FLAGS = ['-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-fstack-protector-all',
         '-D_FORTIFY_SOURCE=2', '-fPIC', '-shared', '-Wl,-z,relro,-z,now,-z,noexecstack',
         '-Wl,--build-id=none']


def rejected(action):
    try:
        action()
    except (ValueError, AssertionError):
        return
    raise AssertionError('Invalid configuration/artifact accepted')


def compile_native(work, enabled):
    binary = work / ('credential.so' if enabled else 'production.so')
    command = ['cc'] + FLAGS
    if enabled:
        command += ['-DIOTBENCH_EMBEDDED_AUTH_ENABLED=1']
    subprocess.run(command + [str(SOURCE / 'fixtures/native/credential.c'), '-o', str(binary)],
                   check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    return binary


def snapshot(path):
    return {p.relative_to(path).as_posix(): p.read_bytes()
            for p in path.rglob('*') if p.is_file()}


def stages(work):
    binary = compile_native(work, True)
    production = compile_native(work, False)
    again = work / 'compile-again'
    again.mkdir()
    assert binary.read_bytes() == compile_native(again, True).read_bytes()
    production_lib = ctypes.CDLL(str(production))
    production_lib.fixture_auth.argtypes = (ctypes.c_char_p, ctypes.c_char_p)
    for item in INVENTORY.values():
        assert item['password'].encode() not in production.read_bytes()
        assert item['username'].encode() not in production.read_bytes()
        assert production_lib.fixture_auth(item['username'].encode(), item['password'].encode()) == 0
    elf = subprocess.run(['readelf', '-W', '-l', '-d', '-s', str(binary)],
                         check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True).stdout
    assert 'GNU_RELRO' in elf and 'BIND_NOW' in elf and '__stack_chk_fail' in elf
    stack = next(line for line in elf.splitlines() if 'GNU_STACK' in line)
    assert 'RWE' not in stack
    assert 'fixture_auth' in elf
    for machine in LIB['MACHINES']:
        try:
            LIB['validate_elf'](binary.read_bytes(), machine)
        except ValueError:
            output = work / 'wrong-target'
            rejected(lambda: BUILD['stage'](output, 'fixture', '1', machine, 'native', binary))
            assert not output.exists()
    print('PASS compiled ELF extraction, native production stub, deterministic compile, RELRO/NOW/NX/stack protector')

    for variant in LIB['VARIANTS']:
        item = INVENTORY[variant]
        machine = 'qemuarm64'
        if variant == 'native':
            for candidate in LIB['MACHINES']:
                try:
                    LIB['validate_elf'](binary.read_bytes(), candidate)
                    machine = candidate
                    break
                except ValueError:
                    continue
            else:
                raise AssertionError('Host compiler architecture must match a supported QEMU target')
        kwargs = dict(mode='fixture', enabled='1', machine=machine, variant=variant,
                      native_binary=binary if variant == 'native' else None)
        rootfs = work / variant
        root = BUILD['stage'](rootfs, **kwargs)
        VERIFY(rootfs, variant)
        RUNTIME['authenticate'](root, work)
        # A normal invocation and a production/missing build marker cannot start.
        command = [sys.executable, '-B', str(root / 'fixture-service.py'),
                   '--runtime-dir', str(work / 'runtime')]
        assert subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5).returncode == 77
        config = root / 'build-config.json'
        saved = config.read_bytes()
        config.write_text('{"mode":"production","enabled":"1","machine":"qemuarm64","variant":"'+variant+'"}')
        assert subprocess.run(command + ['--isolated-fixture'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5).returncode == 77
        config.unlink()
        assert subprocess.run(command + ['--isolated-fixture'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5).returncode == 77
        config.write_bytes(saved)
        assert not (work / 'runtime').exists()
        second = work / (variant + '-again')
        BUILD['stage'](second, **kwargs)
        assert snapshot(rootfs) == snapshot(second)
        if variant == 'native':
            # Prove the compiled implementation authenticates without source.
            (root / item['file']).unlink()
            good = json.dumps(dict(username=item['username'], password=item['password'])).encode()+b'\n'
            with RUNTIME['service'](root, work) as endpoint:
                assert RUNTIME['request'](endpoint, good) == b'OK\n'
            shutil.copyfile(SOURCE / 'fixtures/native/credential.c', root / item['file'])
        else:
            # Change the real artifact, keeping the request and all metadata fixed:
            # the old pair stops authenticating, the new artifact pair succeeds.
            artifact = root / item['file']
            content = artifact.read_bytes()
            replacement = item['password'] + '_changed'
            if variant == 'base64':
                old = base64.b64encode((item['username']+':'+item['password']).encode())
                new = base64.b64encode((item['username']+':'+replacement).encode())
            else:
                old, new = item['password'].encode(), replacement.encode()
            artifact.write_bytes(content.replace(old, new))
            rejected(lambda: VERIFY(rootfs, variant))
            with RUNTIME['service'](root, work) as endpoint:
                for password, result in ((item['password'], b'DENIED\n'), (replacement, b'OK\n')):
                    data = json.dumps(dict(username=item['username'], password=password)).encode()+b'\n'
                    assert RUNTIME['request'](endpoint, data) == result
            artifact.write_bytes(content)
        # Any extra store, including unlisted synthetic pairs, fails extraction checks.
        extra = rootfs / 'extra.conf'
        extra.write_text('username=fixture798_unlisted\npassword=SYNTH_ONLY_798_unlisted_P9!\n')
        rejected(lambda: VERIFY(rootfs, variant))
        extra.unlink()
        VERIFY(rootfs, variant)
    print('PASS 8 generated artifact trees: one pair each, socket accept/deny, malformed requests, actual artifact use, reproducibility')
    print('PASS runtime opt-in, production/missing-marker refusal, private socket permissions and cleanup')


def policies(work):
    for mode, enabled, machine, variant in itertools.product(
            ('production', 'fixture'), ('0', '1'), LIB['MACHINES']+('hardware',), LIB['VARIANTS']+('unknown',)):
        action = lambda: LIB['validate_build'](mode, enabled, machine, variant)
        if mode == 'fixture' and enabled == '1' and machine in LIB['MACHINES'] and variant in LIB['VARIANTS']:
            action()
        else:
            rejected(action)
    for mode, enabled, machine in (('production','1','qemuarm64'), ('fixture','0','qemuarm64'), ('fixture','1','board')):
        output = work / 'refused'
        rejected(lambda: BUILD['stage'](output, mode, enabled, machine, 'json'))
        assert not output.exists()
    output = work / 'default-cli'
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/build-embedded-auth-fixture.py'),
                             '--output', str(output), '--variant', 'json'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
    assert result.returncode == 2 and not output.exists()
    for variant in LIB['VARIANTS']:
        # Duplicates must fail in the format parser, rather than silently choosing a pair.
        source = SOURCE / 'fixtures' / variant / LIB['FILES'][variant]
        duplicate = work / ('duplicate-'+variant)
        content = source.read_text()
        if variant in ('json','base64'):
            content = '{' + content.lstrip()[1:-2] + ',' + content.lstrip()[1:]
        elif variant == 'xml':
            content = content.replace('</authentication>', '<username>extra</username></authentication>')
        else:
            content += content
        duplicate.write_text(content)
        rejected(lambda: LIB['read_pair'](duplicate, variant))
    print('PASS all build-policy combinations, no production writes, duplicate-pair rejection in every representation')


def recipe_code(path, name):
    return textwrap.dedent(path.read_text().split('python '+name+'() {\n')[1].split('\n}')[0])


def integration(work):
    devices = sorted(p.parent.name for p in (LAYER / 'recipes-devices').glob('*/device-*.inc'))
    recipes = LAYER / 'recipes-images'
    expected = {'iotbench-'+d+'-cwe798-embedded-auth-'+v+'.bb' for d,v in itertools.product(devices, LIB['VARIANTS'])}
    assert expected == {p.name for p in recipes.glob('iotbench-*-cwe798-embedded-auth-*.bb')}
    for device, variant in itertools.product(devices, LIB['VARIANTS']):
        text = (recipes / ('iotbench-'+device+'-cwe798-embedded-auth-'+variant+'.bb')).read_text()
        assert 'require recipes-devices/'+device+'/device-'+device+'.inc' in text
        assert 'IOTBENCH_EMBEDDED_AUTH_VARIANT = "'+variant+'"' in text
        assert 'require recipes-images/iotbench-embedded-auth.inc' in text
    for variant in LIB['VARIANTS']:
        assert (SOURCE.parent / ('cwe798-embedded-auth-'+variant+'_1.0.bb')).read_text() == (
            'require cwe798-embedded-auth.inc\nIOTBENCH_EMBEDDED_AUTH_VARIANT = "'+variant+'"\n')
    for path in LAYER.rglob('*.bb'):
        if path.name not in expected and not path.name.startswith('cwe798-embedded-auth-'):
            assert 'cwe798-embedded-auth' not in path.read_text()

    class Parse:
        SkipRecipe = ValueError
        @staticmethod
        def mark_dependency(data, path):
            assert Path(path).is_file()

    class BB:
        parse = Parse
        @staticmethod
        def fatal(message):
            raise ValueError(message)

    class Data:
        def __init__(self, mode, enabled, machine, variant):
            package = 'cwe798-embedded-auth-'+variant
            self.values = dict(IOTBENCH_BUILD_MODE=mode, IOTBENCH_ENABLE_EMBEDDED_AUTH_FIXTURE=enabled,
                               MACHINE=machine, IOTBENCH_EMBEDDED_AUTH_VARIANT=variant,
                               THISDIR=str(SOURCE.parent), IOTBENCH_EMBEDDED_AUTH_LAYER=str(LAYER),
                               IOTBENCH_VULN_INSTALL=package, datadir='/usr/share',
                               IMAGE_INSTALL='packagegroup-core-boot '+package,
                               EXTRA_USERS_PARAMS="usermod -p '!' root;")
        def getVar(self, key):
            return self.values.get(key)

    for path, name in ((SOURCE.parent/'cwe798-embedded-auth.inc','__anonymous'),
                       (recipes/'iotbench-embedded-auth.inc','iotbench_embedded_auth_guard')):
        code = recipe_code(path, name)
        for mode, enabled, machine, variant in itertools.product(
                ('production','fixture'), ('0','1'), LIB['MACHINES']+('board',), LIB['VARIANTS']+('unknown',)):
            action = lambda: exec(code, dict(d=Data(mode, enabled, machine, variant), bb=BB))
            if mode=='fixture' and enabled=='1' and machine in LIB['MACHINES'] and variant in LIB['VARIANTS']:
                action()
            else:
                rejected(action)
        if name != '__anonymous':
            for key, bad in (('IMAGE_INSTALL','packagegroup-core-boot cwe999-extra'),
                             ('EXTRA_USERS_PARAMS','unlocked'), ('IMAGE_FEATURES','debug-tweaks'),
                             ('EXTRA_IMAGE_FEATURES','ssh-server-dropbear')):
                data = Data('fixture','1','qemuarm64','json')
                data.values[key] = bad
                rejected(lambda: exec(code, dict(d=data, bb=BB)))

    # Execute the actual rootfs postprocessor against a generated image tree.
    rootfs = work / 'metadata-rootfs'
    BUILD['stage'](rootfs, 'fixture', '1', 'qemuarm64', 'json')
    (rootfs/'etc').mkdir()
    (rootfs/'etc/shadow').write_text('root:!:0:0:99999:7:::\n')
    for device in devices:
        data = Data('fixture','1','qemuarm64','json')
        data.values.update(IMAGE_ROOTFS=str(rootfs), IOTBENCH_DEVICE=device)
        exec(recipe_code(recipes/'iotbench-embedded-auth.inc','iotbench_embedded_auth_metadata'), dict(d=data, bb=BB))
        assert (rootfs/'etc/iotbench/device.conf').read_bytes() == (LAYER/'recipes-devices'/device/'files/device.conf').read_bytes()
    (rootfs/'etc/shadow').write_text('root:$6$fixed:0:0:99999:7:::\n')
    rejected(lambda: VERIFY(rootfs, 'json', firmware=True))
    print('PASS 88 device/variant image recipes, 8 packages, actual recipe guards and all device metadata postprocessors (BitBake stubs)')


def wrappers(work):
    directory = work / 'wrapper'
    directory.mkdir()
    hook = directory/'hook'
    hook.write_text('source() { export BUILDDIR="$TEST_BUILD" MACHINE=qemuarm64; }\n'
                    'bitbake() { "$TEST_PYTHON" "$TEST_STUB" "$@"; }\n')
    stub = directory/'stub.py'
    stub.write_text(textwrap.dedent('''\
        import os, pathlib, sys, json
        args = sys.argv[1:]
        assert args[0] == '-r'
        config = pathlib.Path(args[1])
        assert config.read_text() == 'IOTBENCH_BUILD_MODE = "fixture"\\nIOTBENCH_ENABLE_EMBEDDED_AUTH_FIXTURE = "1"\\n'
        pathlib.Path(os.environ['TEST_RECORD']).write_text(json.dumps(args))
        if os.environ.get('TEST_FAIL') == '1':
            sys.exit(42)
        deploy = pathlib.Path(os.environ['TEST_BUILD'])/'tmp/deploy/images/qemuarm64'
        deploy.mkdir(parents=True, exist_ok=True)
        (deploy/(args[2]+'-qemuarm64.rootfs.qemuboot.conf')).write_text('kernel_imagetype = Image\\n')
        (deploy/(args[2]+'-qemuarm64.rootfs.ext4.zst')).write_bytes(b'stub')
        (deploy/'Image').write_bytes(b'stub')
        '''))
    script = directory/'wrapper.sh'
    script.write_text((ROOT/'scripts/container-build-and-export.sh').read_text().replace('EXPORT_DIR="/export/', 'EXPORT_DIR="'+str(directory/'export')+'/'))
    env = {k:v for k,v in os.environ.items() if not k.startswith('IOTBENCH_')}
    env.update(BASH_ENV=str(hook),TEST_PYTHON=sys.executable,TEST_STUB=str(stub),TEST_BUILD=str(directory/'build'),
               TEST_RECORD=str(directory/'record'),FIRMWARE='router-cwe798-embedded-auth-json',
               IOTBENCH_ENABLE_EMBEDDED_AUTH_FIXTURE='1', IOTBENCH_BUILD_MODE='fixture')
    for fail in ('0','1'):
        result = subprocess.run(['bash',str(script)],env=dict(env, TEST_FAIL=fail),stdout=subprocess.PIPE, stderr=subprocess.PIPE,timeout=10)
        assert result.returncode == (0 if fail=='0' else 42), result.stderr
        args = json.loads((directory/'record').read_text())
        assert args[2] == 'iotbench-router-cwe798-embedded-auth-json' and not Path(args[1]).exists()
    for overrides in ({'IOTBENCH_BUILD_MODE':'production'}, {'FIRMWARE':'router-cwe078-os-command-injection'},
                      *({name:'1'} for name in ('IOTBENCH_ENABLE_REST_FIXTURE','IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE',
                                               'IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE','IOTBENCH_ENABLE_TELNET_FIXTURE',
                                               'IOTBENCH_ENABLE_SUDO_ENV_FIXTURE','IOTBENCH_ENABLE_FTP_WRITE_FIXTURE'))):
        if (directory/'record').exists():
            (directory/'record').unlink()
        assert subprocess.run(['bash',str(script)],env=dict(env,**overrides),stdout=subprocess.PIPE, stderr=subprocess.PIPE,timeout=10).returncode != 0
        assert not (directory/'record').exists()
    bindir = directory/'bin'
    bindir.mkdir()
    docker = bindir/'docker'
    docker.write_text('#!/usr/bin/env python3\nimport json,os,sys\n'
                      'with open(os.environ["TEST_CATALOG"],"a") as f:\n'
                      '    f.write(json.dumps([os.environ["FIRMWARE"],sys.argv[1:]])+"\\n")\n')
    docker.chmod(0o755)
    catalog = directory/'catalog'
    for enabled in ('0','1'):
        if catalog.exists():
            catalog.unlink()
        current = dict(env, PATH=str(bindir)+os.pathsep+env['PATH'], TEST_CATALOG=str(catalog),
                       IOTBENCH_ENABLE_EMBEDDED_AUTH_FIXTURE=enabled, MACHINES='qemuarm64')
        assert subprocess.run(['sh',str(ROOT/'scripts/build-all.sh')],env=current,stdout=subprocess.PIPE, stderr=subprocess.PIPE,timeout=45).returncode == 0
        entries = [json.loads(line) for line in catalog.read_text().splitlines()]
        selected = [args for firmware,args in entries if '-cwe798-embedded-auth-' in firmware]
        assert len(selected) == (88 if enabled=='1' else 0)
        assert all('IOTBENCH_ENABLE_EMBEDDED_AUTH_FIXTURE=1' in args and 'IOTBENCH_BUILD_MODE=fixture' in args for args in selected)
    print('PASS real build/catalog wrappers with stubs: default exclusion, opt-in, mixed/production refusal, temporary config cleanup')


def filesystem_roundtrip(work):
    """Build actual ext4 artifacts from staged payloads and inspect extracted files."""
    mke2fs = shutil.which('mke2fs') or '/usr/sbin/mke2fs'
    debugfs = shutil.which('debugfs') or '/usr/sbin/debugfs'
    for variant in LIB['VARIANTS']:
        staged = work / variant
        image = work / (variant+'.ext4')
        subprocess.run([mke2fs, '-q', '-t', 'ext4', '-F', '-d', str(staged), str(image), '8192'],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        extracted = work / (variant+'-extracted')
        extracted.mkdir()
        subprocess.run([debugfs, '-R', 'rdump / '+str(extracted), str(image)],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        # debugfs preserves contents; use it to inspect the actual filesystem image.
        for path, data in snapshot(staged).items():
            assert (extracted/path).read_bytes() == data
        VERIFY(extracted, variant)
        RUNTIME['authenticate'](extracted/'usr/share/iotbench/embedded-auth'/variant, work)
    print('PASS 8 generated ext4 images: extracted artifact bytes, credential recovery and socket authentication')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--isolated-fixture', action='store_true')
    parser.add_argument('--rootfs', type=Path, help='Inspect an extracted generated rootfs, including ELF')
    parser.add_argument('--variant', choices=LIB['VARIANTS'])
    parser.add_argument('--production-rootfs', type=Path, help='Inspect an extracted normal rootfs for fixture exclusion')
    parser.add_argument('--filesystem-roundtrip', action='store_true', help='Also build/extract ext4 artifacts using mke2fs/debugfs')
    args = parser.parse_args()
    if not args.isolated_fixture:
        parser.exit(77, 'Tests require --isolated-fixture\n')
    if args.production_rootfs:
        VERIFY(args.production_rootfs, None, production=True)
        print('PASS production rootfs excludes fixture artifacts and credentials')
        return
    if args.rootfs:
        if not args.variant:
            parser.error('--rootfs requires --variant')
        VERIFY(args.rootfs, args.variant, firmware=True)
        print('PASS generated firmware artifacts, one synthetic pair, locked local accounts')
        return
    with tempfile.TemporaryDirectory(prefix='auth798-') as temp:
        work = Path(temp)
        policies(work)
        stages(work)
        integration(work)
        wrappers(work)
        if args.filesystem_roundtrip:
            filesystem_roundtrip(work)
        empty = work/'production-rootfs'
        empty.mkdir()
        VERIFY(empty, None, production=True)
        (empty/'unexpected').write_text(INVENTORY['json']['password'])
        rejected(lambda: VERIFY(empty, None, production=True))
    print('PASS all embedded-auth fixture checks (offline host builds; no target firmware build claimed)')


if __name__ == '__main__':
    main()
