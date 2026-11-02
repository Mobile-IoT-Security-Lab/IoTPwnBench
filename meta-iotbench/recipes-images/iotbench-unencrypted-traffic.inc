# Retain the catalog scenario ID; native login uses normal account authentication.
IOTBENCH_CWE = "CWE-319 CWE-798"
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
    test -L ${IMAGE_ROOTFS}${sbindir}/telnetd || test -x ${IMAGE_ROOTFS}${sbindir}/telnetd || bbfatal "Native Telnet daemon is missing"
    test -L ${IMAGE_ROOTFS}/bin/login || test -x ${IMAGE_ROOTFS}/bin/login || bbfatal "System login is missing"
    grep -q '^maintenance:' ${IMAGE_ROOTFS}${sysconfdir}/shadow || bbfatal "Maintenance account is missing"
    cat ${IMAGE_ROOTFS}${datadir}/iotbench/unencrypted-traffic/NOTICE >> ${IMAGE_ROOTFS}${sysconfdir}/motd
}
