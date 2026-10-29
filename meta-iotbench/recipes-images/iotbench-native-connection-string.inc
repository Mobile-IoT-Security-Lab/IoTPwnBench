# Device identity is retained without installing unrelated device services.
IOTBENCH_CONNECTION_LAYER := "${THISDIR}/.."
IOTBENCH_BUILD_MODE ?= "production"
IOTBENCH_ENABLE_CONNECTION_FIXTURE ?= "0"
IOTBENCH_DEVICE_INSTALL = ""
IMAGE_INSTALL = "packagegroup-core-boot ${IOTBENCH_VULN_INSTALL}"

python iotbench_native_connection_guard() {
    expected = 'cwe020-native-connection-string'
    if (d.getVar('IOTBENCH_BUILD_MODE') != 'fixture' or
            d.getVar('IOTBENCH_ENABLE_CONNECTION_FIXTURE') != '1'):
        bb.fatal('Native connection fixtures require explicit opt-in and fixture mode')
    if (d.getVar('IOTBENCH_CWE') != 'CWE-20' or
            d.getVar('IOTBENCH_VULN_INSTALL') != expected or
            set((d.getVar('IMAGE_INSTALL') or '').split()) != {'packagegroup-core-boot', expected}):
        bb.fatal('Native connection fixtures require exactly one CWE-20 package and no device daemons')
}
do_rootfs[prefuncs] += "iotbench_native_connection_guard"
ROOTFS_POSTPROCESS_COMMAND += "iotbench_native_connection_metadata; "

python iotbench_native_connection_metadata() {
    import pathlib
    import shutil
    root = pathlib.Path(d.getVar('IMAGE_ROOTFS'))
    target = root / d.getVar('sysconfdir').lstrip('/')
    (target / 'iotbench').mkdir(parents=True, exist_ok=True)
    device = d.getVar('IOTBENCH_DEVICE')
    profile = pathlib.Path(d.getVar('IOTBENCH_CONNECTION_LAYER')) / 'recipes-devices' / device / 'files'
    for name in ('device.conf', 'peripherals.conf'):
        shutil.copyfile(profile / name, target / 'iotbench' / name)
    helper = root / d.getVar('bindir').lstrip('/') / 'fixture-connection'
    if helper.is_symlink() or helper.stat().st_mode & 0o7777 != 0o755 or helper.stat().st_uid != 0 or helper.stat().st_gid != 0:
        bb.fatal('Native connection fixture must be ordinary root:root 0755')
    data = root / d.getVar('datadir').lstrip('/') / 'iotbench/native-connection-string'
    with (target / 'motd').open('ab') as output:
        output.write((data / 'NOTICE').read_bytes())
    manifest = pathlib.Path(d.getVar('IMAGE_MANIFEST'))
    if manifest.exists():
        packages = [line.split()[0] for line in manifest.read_text().splitlines() if line.split()]
        if [p for p in packages if p.startswith('cwe')] != ['cwe020-native-connection-string']:
            bb.fatal('Unexpected vulnerability packages in native connection fixture image')
}
