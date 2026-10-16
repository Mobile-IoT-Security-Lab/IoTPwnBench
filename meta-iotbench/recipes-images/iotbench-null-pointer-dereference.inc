# Mark every image and reject unintended elevated permissions on the helper.
ROOTFS_POSTPROCESS_COMMAND += "iotbench_null_pointer_dereference_metadata; "

iotbench_null_pointer_dereference_metadata() {
    if [ "$(stat -c '%u:%g:%a' "${IMAGE_ROOTFS}${bindir}/fixture-device-info")" != "0:0:755" ]; then
        bbfatal "Native null-pointer fixture helper must be ordinary root:root 0755"
    fi
    cat ${IMAGE_ROOTFS}${datadir}/iotbench/null-pointer-dereference/NOTICE >> ${IMAGE_ROOTFS}${sysconfdir}/motd
}
