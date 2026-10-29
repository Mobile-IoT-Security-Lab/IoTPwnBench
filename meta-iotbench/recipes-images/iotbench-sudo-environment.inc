# One synthetic sudo environment/diagnostic credential workflow.
IOTBENCH_CWE = "CWE-798"
IOTBENCH_VULN_INSTALL = "cwe798-sudo-environment"
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
    if [ "$(stat -c '%u:%g:%a' '${IMAGE_ROOTFS}${bindir}/fixture-sudo-env')" != "0:0:755" ]; then
        bbfatal "Fixture helper must be ordinary root:root 0755"
    fi
    if [ "$(stat -c '%u:%g:%a' '${IMAGE_ROOTFS}${datadir}/iotbench/sudo-environment/build-config')" != "0:0:644" ]; then
        bbfatal "Fixture runtime build manifest must be root:root 0644"
    fi
    if ! grep -Eq '^[#@]includedir[[:space:]]+${sysconfdir}/sudoers.d' '${IMAGE_ROOTFS}${sysconfdir}/sudoers'; then
        bbfatal "Default sudoers must include the fixture policy directory"
    fi
    cat ${IMAGE_ROOTFS}${datadir}/iotbench/sudo-environment/NOTICE >> ${IMAGE_ROOTFS}${sysconfdir}/motd
}
