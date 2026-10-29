# One weakly configured Telnet scenario; related CWEs describe the same service.
IOTBENCH_CWE = "CWE-798 CWE-287 CWE-276"
IOTBENCH_VULN_INSTALL = "cwe798-unencrypted-traffic"
IOTBENCH_BUILD_MODE ?= "production"
IOTBENCH_ENABLE_TELNET_FIXTURE ?= "0"

python iotbench_telnet_fixture_guard() {
    if (d.getVar('IOTBENCH_BUILD_MODE') != 'fixture' or
            d.getVar('IOTBENCH_ENABLE_TELNET_FIXTURE') != '1' or
            d.getVar('MACHINE') not in ('qemuarm64', 'qemuarm', 'qemux86-64', 'qemux86', 'qemumips')):
        bb.fatal('Telnet image requires explicit fixture build mode, Telnet opt-in and a supported QEMU machine')
}
do_rootfs[prefuncs] += "iotbench_telnet_fixture_guard"
ROOTFS_POSTPROCESS_COMMAND += "iotbench_telnet_fixture_metadata; "

iotbench_telnet_fixture_metadata() {
    if [ "$(stat -c '%u:%g:%a' '${IMAGE_ROOTFS}${sysconfdir}/iotbench/telnet-auth.json')" != "0:0:666" ]; then
        bbfatal "Telnet authentication policy must exhibit the documented root:root 0666 fixture condition"
    fi
    if [ "$(stat -c '%u:%g:%a' '${IMAGE_ROOTFS}${bindir}/fixture-telnet')" != "0:0:755" ]; then
        bbfatal "Telnet helper must be ordinary root:root 0755"
    fi
    cat ${IMAGE_ROOTFS}${datadir}/iotbench/unencrypted-traffic/NOTICE >> ${IMAGE_ROOTFS}${sysconfdir}/motd
}
