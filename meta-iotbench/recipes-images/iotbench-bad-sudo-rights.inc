# Mark every sudo traversal image on the serial console as well as in the
# installed fixture NOTICE and machine-readable ground truth.
ROOTFS_POSTPROCESS_COMMAND += "iotbench_sudo_fixture_notice; "

iotbench_sudo_fixture_notice() {
    cat ${IMAGE_ROOTFS}${datadir}/iotbench/bad-sudo-rights/NOTICE >> ${IMAGE_ROOTFS}${sysconfdir}/motd
}
