ROOTFS_POSTPROCESS_COMMAND += "iotbench_service_buffer_overflow_metadata; "

iotbench_service_buffer_overflow_metadata() {
    if [ "$(stat -c '%u:%g:%a' "${IMAGE_ROOTFS}${bindir}/fixture-label-service")" != "0:0:755" ]; then
        bbfatal "Native service fixture must be ordinary root:root 0755"
    fi
    cat ${IMAGE_ROOTFS}${datadir}/iotbench/service-buffer-overflow/NOTICE >> ${IMAGE_ROOTFS}${sysconfdir}/motd
}
