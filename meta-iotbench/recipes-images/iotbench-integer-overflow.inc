# Mark every fixture image and verify ordinary executable permissions.
ROOTFS_POSTPROCESS_COMMAND += "iotbench_integer_overflow_metadata; "

iotbench_integer_overflow_metadata() {
    if [ "$(stat -c '%u:%g:%a' "${IMAGE_ROOTFS}${bindir}/fixture-batch-size")" != "0:0:755" ]; then
        bbfatal "Native integer-overflow fixture helper must be ordinary root:root 0755"
    fi
    cat ${IMAGE_ROOTFS}${datadir}/iotbench/integer-overflow/NOTICE >> ${IMAGE_ROOTFS}${sysconfdir}/motd
}
