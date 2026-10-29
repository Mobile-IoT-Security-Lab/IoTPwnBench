# Retain device identity, with no dashboard, network daemons or other defects.
IOTBENCH_JAVA_COMMAND_LAYER := "${THISDIR}/.."
IOTBENCH_BUILD_MODE ?= "production"
IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE ?= "0"
IOTBENCH_DEVICE_INSTALL = ""
IMAGE_INSTALL = "packagegroup-core-boot ${IOTBENCH_VULN_INSTALL}"
# Room for a disposable copy of the runtime during isolated guest tests.
IMAGE_ROOTFS_EXTRA_SPACE = "524288"

python iotbench_java_command_guard() {
    allowed = {'cwe078-java-os-command-injection', 'cwe077-java-app-command-injection'}
    package = d.getVar('IOTBENCH_VULN_INSTALL')
    if (d.getVar('IOTBENCH_BUILD_MODE') != 'fixture' or
            d.getVar('IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE') != '1'):
        bb.fatal('Java command fixtures require explicit opt-in and fixture mode')
    if (package not in allowed or
            set((d.getVar('IMAGE_INSTALL') or '').split()) != {'packagegroup-core-boot', package}):
        bb.fatal('Java command fixtures require exactly one fixture package and no device daemons')
}
do_rootfs[prefuncs] += "iotbench_java_command_guard"
ROOTFS_POSTPROCESS_COMMAND += "iotbench_java_command_metadata; "

python iotbench_java_command_metadata() {
    import pathlib
    import shutil
    root = pathlib.Path(d.getVar('IMAGE_ROOTFS'))
    etc = root / d.getVar('sysconfdir').lstrip('/')
    (etc / 'iotbench').mkdir(parents=True, exist_ok=True)
    profile = pathlib.Path(d.getVar('IOTBENCH_JAVA_COMMAND_LAYER')) / 'recipes-devices' / d.getVar('IOTBENCH_DEVICE') / 'files'
    for name in ('device.conf', 'peripherals.conf'):
        shutil.copyfile(profile / name, etc / 'iotbench' / name)
    data = root / d.getVar('datadir').lstrip('/') / 'iotbench/java-command-fixture'
    jars = list(data.glob('*.jar'))
    if len(jars) != 1 or jars[0].is_symlink():
        bb.fatal('Exactly one ordinary Java command fixture JAR is required')
    info = jars[0].stat()
    if info.st_uid != 0 or info.st_gid != 0 or info.st_mode & 0o7777 != 0o644:
        bb.fatal('Java command JAR must be root:root 0644')
    with (etc / 'motd').open('ab') as output:
        output.write((data / 'NOTICE').read_bytes())
}
