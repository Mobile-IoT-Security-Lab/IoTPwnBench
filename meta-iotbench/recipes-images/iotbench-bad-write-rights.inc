# Only a deliberately opted-in synthetic image can contain this fixture.
IOTBENCH_ENABLE_FTP_WRITE_FIXTURE ?= "0"
python iotbench_ftp_fixture_guard() {
    if d.getVar("IOTBENCH_ENABLE_FTP_WRITE_FIXTURE") != "1":
        bb.fatal('Synthetic FTP fixture requires IOTBENCH_ENABLE_FTP_WRITE_FIXTURE = "1" in test configuration')
}
do_rootfs[prefuncs] += "iotbench_ftp_fixture_guard"
ROOTFS_POSTPROCESS_COMMAND += "iotbench_ftp_fixture_mask; "
iotbench_ftp_fixture_mask() {
    # The vendor daemon must never start with its default configuration.
    install -d ${IMAGE_ROOTFS}${sysconfdir}/systemd/system
    ln -sf /dev/null ${IMAGE_ROOTFS}${sysconfdir}/systemd/system/vsftpd.service
    ln -sf /dev/null ${IMAGE_ROOTFS}${sysconfdir}/systemd/system/vsftpd.socket
}
