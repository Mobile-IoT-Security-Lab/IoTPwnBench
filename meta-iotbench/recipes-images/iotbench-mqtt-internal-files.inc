# Only these synthetic MQTT images customize the fixture identity and notice.
ROOTFS_POSTPROCESS_COMMAND += "iotbench_mqtt_internal_files_metadata; "

iotbench_mqtt_internal_files_metadata() {
    fixture_data="${IMAGE_ROOTFS}${datadir}/iotbench/mqtt-internal-files"
    sed -i -e 's|@DEVICE@|${IOTBENCH_DEVICE}|g' "$fixture_data/internal/device.conf"
    for fixture_file in device.conf maintenance.dat; do
        if [ "$(stat -c '%u:%g:%a' "$fixture_data/internal/$fixture_file")" != "0:991:640" ]; then
            bbfatal "Internal MQTT fixture file must be root:mqttfixture 0640"
        fi
    done
    if [ "$(stat -c '%u:%g:%a' "$fixture_data/internal")" != "0:991:750" ]; then
        bbfatal "Internal MQTT fixture directory must be root:mqttfixture 0750"
    fi
    cat "$fixture_data/NOTICE" >> ${IMAGE_ROOTFS}${sysconfdir}/motd
}
