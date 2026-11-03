# Native, environment-sensitive maintenance report; keep the catalog's old tag
# for traceability, not as a claim that du demonstrates hardcoded credentials.
IOTBENCH_CWE = "CWE-798"
# A corrected twin sets IOTBENCH_TWIN to 1. It installs the corrected variant of the module.
IOTBENCH_TWIN ?= "0"
IOTBENCH_TWIN_SUFFIX = "${@'-fixed' if d.getVar('IOTBENCH_TWIN') == '1' else ''}"
IOTBENCH_VULN_INSTALL = "cwe798-sudo-environment${IOTBENCH_TWIN_SUFFIX}"
IOTBENCH_BUILD_MODE ?= "production"
IOTBENCH_ENABLE_SUDO_ENV_FIXTURE ?= "0"

python iotbench_sudo_env_fixture_guard() {
    if (d.getVar('IOTBENCH_BUILD_MODE') != 'fixture' or
            d.getVar('IOTBENCH_ENABLE_SUDO_ENV_FIXTURE') != '1' or
            d.getVar('MACHINE') not in ('qemuarm64', 'qemuarm', 'qemux86-64', 'qemux86', 'qemumips')):
        bb.fatal('Sudo environment image requires explicit fixture mode, sudo environment opt-in and a supported QEMU machine')
}
do_rootfs[prefuncs] += "iotbench_sudo_env_fixture_guard"
ROOTFS_POSTPROCESS_COMMAND += "iotbench_sudo_env_fixture_metadata; "

iotbench_sudo_env_fixture_metadata() {
    if [ "$(stat -c '%u:%g:%a' '${IMAGE_ROOTFS}${sysconfdir}/sudoers.d/iotbench-sudo-environment')" != "0:0:440" ]; then
        bbfatal "Fixture sudo policy must be root:root 0440"
    fi
    test -L ${IMAGE_ROOTFS}${base_bindir}/du || test -x ${IMAGE_ROOTFS}${base_bindir}/du || bbfatal "Native du is missing"
    test -L ${IMAGE_ROOTFS}${base_bindir}/id || test -x ${IMAGE_ROOTFS}${base_bindir}/id || bbfatal "Native id is missing"
    test -d ${IMAGE_ROOTFS}${sysconfdir}/iotbench || bbfatal "Device configuration directory is missing"
    test ! -e ${IMAGE_ROOTFS}${bindir}/fixture-sudo-env || bbfatal "Obsolete fixed-response helper is still installed"
    test ! -e ${IMAGE_ROOTFS}${datadir}/iotbench/sudo-environment/test-session.py || bbfatal "Obsolete runtime runner is still installed"
    if ! grep -Eq '^[#@]includedir[[:space:]]+${sysconfdir}/sudoers.d' '${IMAGE_ROOTFS}${sysconfdir}/sudoers'; then
        bbfatal "Default sudoers must include the fixture policy directory"
    fi
    cat ${IMAGE_ROOTFS}${datadir}/iotbench/sudo-environment/NOTICE >> ${IMAGE_ROOTFS}${sysconfdir}/motd
}
