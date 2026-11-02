# Only a deliberately opted-in synthetic image can contain this fixture.
IOTBENCH_ENABLE_FTP_WRITE_FIXTURE ?= "0"
python iotbench_ftp_fixture_guard() {
    if d.getVar("IOTBENCH_ENABLE_FTP_WRITE_FIXTURE") != "1":
        bb.fatal('Synthetic FTP fixture requires IOTBENCH_ENABLE_FTP_WRITE_FIXTURE = "1" in test configuration')
}
do_rootfs[prefuncs] += "iotbench_ftp_fixture_guard"
ROOTFS_POSTPROCESS_COMMAND += "iotbench_ftp_fixture_mask; iotbench_ftp_fixture_exports; "
iotbench_ftp_fixture_mask() {
    # The vendor daemon must never start with its default configuration.
    install -d ${IMAGE_ROOTFS}${sysconfdir}/systemd/system
    ln -sf /dev/null ${IMAGE_ROOTFS}${sysconfdir}/systemd/system/vsftpd.service
    ln -sf /dev/null ${IMAGE_ROOTFS}${sysconfdir}/systemd/system/vsftpd.socket
}

# Export build-time copies of this device's maintenance data. Both directories
# contain the same root-owned, read-only files; only their directory mode differs.
iotbench_ftp_fixture_exports() {
    for ftp_fixture_directory in bad control; do
        install -m 0644 ${IMAGE_ROOTFS}${sysconfdir}/iotbench/device.conf \
            ${IMAGE_ROOTFS}/srv/iotbench-ftp/$ftp_fixture_directory/device.conf
        install -m 0644 ${IMAGE_ROOTFS}${sysconfdir}/iotbench/peripherals.conf \
            ${IMAGE_ROOTFS}/srv/iotbench-ftp/$ftp_fixture_directory/peripherals.conf
        install -m 0644 ${IMAGE_ROOTFS}${localstatedir}/lib/router-dashboard/settings.json \
            ${IMAGE_ROOTFS}/srv/iotbench-ftp/$ftp_fixture_directory/settings.json
    done
}
