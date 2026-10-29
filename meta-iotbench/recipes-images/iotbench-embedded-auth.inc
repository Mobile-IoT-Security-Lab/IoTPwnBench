IOTBENCH_CWE = "CWE-798"
IOTBENCH_VULN_INSTALL = "cwe798-embedded-auth-${IOTBENCH_EMBEDDED_AUTH_VARIANT}"
IOTBENCH_BUILD_MODE ?= "production"
IOTBENCH_ENABLE_EMBEDDED_AUTH_FIXTURE ?= "0"
IOTBENCH_EMBEDDED_AUTH_LAYER := "${THISDIR}/.."

# Keep device identity/peripheral descriptions, but omit its network services.
# The inherited demo console password would introduce another fixed credential.
IOTBENCH_DEVICE_INSTALL = ""
IMAGE_INSTALL = "packagegroup-core-boot ${IOTBENCH_VULN_INSTALL}"
IMAGE_FEATURES = ""
EXTRA_IMAGE_FEATURES = ""
ROOT_PASSWORD_HASH = ""
EXTRA_USERS_PARAMS = "usermod -p '!' root;"

python iotbench_embedded_auth_guard() {
    import runpy
    layer = d.getVar('IOTBENCH_EMBEDDED_AUTH_LAYER')
    try:
        runpy.run_path(layer + '/recipes-vulns/cwe798-embedded-auth/files/fixture-lib.py')['validate_build'](
            d.getVar('IOTBENCH_BUILD_MODE'), d.getVar('IOTBENCH_ENABLE_EMBEDDED_AUTH_FIXTURE'),
            d.getVar('MACHINE'), d.getVar('IOTBENCH_EMBEDDED_AUTH_VARIANT'))
    except ValueError as error:
        bb.fatal(str(error))
    expected = 'cwe798-embedded-auth-' + d.getVar('IOTBENCH_EMBEDDED_AUTH_VARIANT')
    if (d.getVar('IOTBENCH_VULN_INSTALL') != expected or
            (d.getVar('IMAGE_INSTALL') or '').split() != ['packagegroup-core-boot', expected]):
        bb.fatal('Embedded auth images require exactly one fixture and the minimal boot package group')
    if d.getVar('EXTRA_USERS_PARAMS') != "usermod -p '!' root;":
        bb.fatal('Embedded auth images must lock the inherited console password')
    if (d.getVar('IMAGE_FEATURES') or '').strip() or (d.getVar('EXTRA_IMAGE_FEATURES') or '').strip():
        bb.fatal('Embedded auth images cannot add debug login or network service features')
}
do_rootfs[prefuncs] += "iotbench_embedded_auth_guard"
ROOTFS_POSTPROCESS_COMMAND += "iotbench_embedded_auth_metadata; "

python iotbench_embedded_auth_metadata() {
    import pathlib
    import runpy
    rootfs = pathlib.Path(d.getVar('IMAGE_ROOTFS'))
    layer = pathlib.Path(d.getVar('IOTBENCH_EMBEDDED_AUTH_LAYER'))
    device = d.getVar('IOTBENCH_DEVICE')
    destination = rootfs / 'etc/iotbench'
    destination.mkdir(parents=True, exist_ok=True)
    for name in ('device.conf', 'peripherals.conf'):
        (destination / name).write_bytes((layer / 'recipes-devices' / device / 'files' / name).read_bytes())
        (destination / name).chmod(0o644)
    tests = runpy.run_path(str(layer / 'recipes-vulns/cwe798-embedded-auth/files/fixture-verify.py'))
    try:
        tests['verify'](rootfs, d.getVar('IOTBENCH_EMBEDDED_AUTH_VARIANT'), firmware=True)
    except (ValueError, AssertionError) as error:
        bb.fatal(str(error))
}
