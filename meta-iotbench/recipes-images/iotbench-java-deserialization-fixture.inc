# Preserve device identity while excluding unrelated applications and daemons.
IOTBENCH_JAVA_DESERIALIZATION_LAYER := "${THISDIR}/.."
IOTBENCH_BUILD_MODE ?= "production"
IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE ?= "0"
IOTBENCH_DEVICE_INSTALL = ""
IMAGE_INSTALL = "packagegroup-core-boot ${IOTBENCH_VULN_INSTALL}"
IMAGE_ROOTFS_EXTRA_SPACE = "524288"

python iotbench_java_deserialization_guard() {
    # A corrected twin installs the -fixed package, with IOTBENCH_CWE reset to
    # 'none' and the original CWE kept in IOTBENCH_CORRECTS_CWE.
    package = 'cwe502-java-deserialization'
    twin = (d.getVar('IOTBENCH_VULN_INSTALL') or '').endswith('-fixed')
    if twin:
        package = package + '-fixed'
    if (d.getVar('IOTBENCH_BUILD_MODE') != 'fixture' or
            d.getVar('IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE') != '1'):
        bb.fatal('Java deserialization requires explicit opt-in and fixture mode')
    if (d.getVar('IOTBENCH_VULN_INSTALL') != package or
            set((d.getVar('IMAGE_INSTALL') or '').split()) != {'packagegroup-core-boot', package}):
        bb.fatal('Java deserialization images require one fixture and no device daemons')
}
do_rootfs[prefuncs] += "iotbench_java_deserialization_guard"
ROOTFS_POSTPROCESS_COMMAND += "iotbench_java_deserialization_metadata; "

python iotbench_java_deserialization_metadata() {
    import pathlib
    import shutil
    root = pathlib.Path(d.getVar('IMAGE_ROOTFS'))
    etc = root / d.getVar('sysconfdir').lstrip('/')
    (etc / 'iotbench').mkdir(parents=True, exist_ok=True)
    profile = pathlib.Path(d.getVar('IOTBENCH_JAVA_DESERIALIZATION_LAYER')) / 'recipes-devices' / d.getVar('IOTBENCH_DEVICE') / 'files'
    for name in ('device.conf', 'peripherals.conf'):
        shutil.copyfile(profile / name, etc / 'iotbench' / name)
    data = root / d.getVar('datadir').lstrip('/') / 'iotbench/java-deserialization-fixture'
    jars = sorted(data.glob('*.jar'))
    if {jar.name for jar in jars} != {'fixture-deserialization.jar', 'fixture-deserialization-tests.jar'}:
        bb.fatal('Expected exactly the application and test harness JARs')
    for jar in jars:
        info = jar.stat()
        if jar.is_symlink() or info.st_uid != 0 or info.st_gid != 0 or info.st_mode & 0o7777 != 0o644:
            bb.fatal('Java fixture JARs must be ordinary root:root 0644 files')
    with (etc / 'motd').open('ab') as output:
        output.write((data / 'NOTICE').read_bytes())
}
