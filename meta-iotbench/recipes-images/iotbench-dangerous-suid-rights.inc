# Keep the warning visible on login and fail image generation if SUID metadata
# was lost during packaging. The final ext4 metadata is also checked offline.
ROOTFS_POSTPROCESS_COMMAND += "iotbench_suid_fixture_metadata; "

iotbench_suid_fixture_metadata() {
    fixture_helper="${IMAGE_ROOTFS}${bindir}/iotbench-suid-fixture"
    if [ "$(stat -c '%u:%g:%a' "$fixture_helper")" != "0:0:4755" ]; then
        bbfatal "Synthetic SUID helper must be root:root with mode 4755"
    fi
    cat ${IMAGE_ROOTFS}${datadir}/iotbench/dangerous-suid-rights/NOTICE >> ${IMAGE_ROOTFS}${sysconfdir}/motd
}
