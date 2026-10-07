# Keep device identity deterministic and preserve private file permissions.
ROOTFS_POSTPROCESS_COMMAND += "iotbench_coap_internal_files_metadata; "

iotbench_coap_internal_files_metadata() {
    fixture_data="${IMAGE_ROOTFS}${datadir}/iotbench/coap-internal-files"
    sed -i -e 's|@DEVICE@|${IOTBENCH_DEVICE}|g' "$fixture_data/internal/device.conf"
    for fixture_file in device.conf maintenance.dat; do
        if [ "$(stat -c '%u:%g:%a' "$fixture_data/internal/$fixture_file")" != "0:992:640" ]; then
            bbfatal "Internal CoAP fixture file must be root:coapfixture 0640"
        fi
    done
    if [ "$(stat -c '%u:%g:%a' "$fixture_data/internal")" != "0:992:750" ]; then
        bbfatal "Internal CoAP fixture directory must be root:coapfixture 0750"
    fi
    cat "$fixture_data/NOTICE" >> ${IMAGE_ROOTFS}${sysconfdir}/motd
}
