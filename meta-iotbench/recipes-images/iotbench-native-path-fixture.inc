# Minimal test-only images retain device identity, without its service daemons.
IOTBENCH_BUILD_MODE ?= "production"
IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE ?= "0"
IOTBENCH_PATH_LAYER := "${THISDIR}/.."
IOTBENCH_DEVICE_INSTALL = ""
IOTBENCH_CWE = "CWE-${@int(d.getVar('PATH_FIXTURE_CWE'))}"
IOTBENCH_VULN_INSTALL = "${PATH_FIXTURE_PACKAGE}"
IMAGE_INSTALL = "packagegroup-core-boot ${IOTBENCH_VULN_INSTALL}"

python iotbench_native_path_guard() {
    import runpy
    policy = d.getVar('IOTBENCH_PATH_LAYER') + '/recipes-vulns/native-path-fixture/files/fixture-build.py'
    try:
        runpy.run_path(policy)['validate_build'](d.getVar('IOTBENCH_BUILD_MODE'),
            d.getVar('IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE'), d.getVar('MACHINE'))
    except ValueError as error:
        bb.fatal(str(error))
    variants = {'022': 'cwe022-native-path-traversal', '020': 'cwe020-native-filename-validation'}
    expected = variants.get(d.getVar('PATH_FIXTURE_CWE'))
    if (not expected or d.getVar('PATH_FIXTURE_PACKAGE') != expected or
            d.getVar('IOTBENCH_VULN_INSTALL') != expected or
            set((d.getVar('IMAGE_INSTALL') or '').split()) != {'packagegroup-core-boot', expected}):
        bb.fatal('Native path fixture images require exactly their own variant and no device daemons')
}
do_rootfs[prefuncs] += "iotbench_native_path_guard"
ROOTFS_POSTPROCESS_COMMAND += "iotbench_native_path_metadata; "

python iotbench_native_path_metadata() {
    import hashlib
    import json
    import pathlib
    import shutil
    root = pathlib.Path(d.getVar('IMAGE_ROOTFS'))
    target = root / 'etc/iotbench'
    target.mkdir(parents=True, exist_ok=True)
    device = d.getVar('IOTBENCH_DEVICE')
    source = pathlib.Path(d.getVar('IOTBENCH_PATH_LAYER')) / 'recipes-devices' / device / 'files'
    for name in ('device.conf', 'peripherals.conf'):
        shutil.copyfile(source / name, target / name)
    base = root / d.getVar('datadir').lstrip('/') / 'iotbench/native-path'
    info = json.loads((base / 'variant.json').read_text())
    if info['cwe'] != d.getVar('PATH_FIXTURE_CWE') or info['binary_origin'] != 'target':
        bb.fatal('Wrong native path artifact variant/origin')
    for path in [base] + list(base.rglob('*')):
        expected = 0o755 if path.is_dir() or path.parent == base / 'bin' else 0o644
        if (path.is_symlink() or path.stat().st_uid != 0 or path.stat().st_gid != 0 or
                path.stat().st_mode & 0o7777 != expected):
            bb.fatal('Native path fixtures require ordinary root-owned files and directories')
    for name, digest in info['sha256'].items():
        if hashlib.sha256((base / 'bin' / name).read_bytes()).hexdigest() != digest:
            bb.fatal('Packaging changed native path artifact ELF bytes')
    manifest = pathlib.Path(d.getVar('IMAGE_MANIFEST'))
    if manifest.exists():
        packages = [line.split()[0] for line in manifest.read_text().splitlines() if line.split()]
        if [p for p in packages if p.startswith('cwe')] != [d.getVar('PATH_FIXTURE_PACKAGE')]:
            bb.fatal('Unexpected vulnerability packages in native path fixture image')
}
