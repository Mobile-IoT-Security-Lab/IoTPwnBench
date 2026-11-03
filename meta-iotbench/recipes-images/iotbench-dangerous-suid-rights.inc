# Keep the warning visible on login and fail image generation if SUID metadata
# was lost during packaging. The final ext4 metadata is also checked offline.
ROOTFS_POSTPROCESS_COMMAND += "iotbench_suid_fixture_metadata; "

iotbench_suid_fixture_metadata() {
    # A corrected twin installs the helper without the SUID bit, see IOTBENCH_VULN_INSTALL.
    case "${IOTBENCH_VULN_INSTALL}" in
        *-fixed) expected_mode="0:0:755" ;;
        *) expected_mode="0:0:4755" ;;
    esac
    fixture_helper="${IMAGE_ROOTFS}${bindir}/iotbench-suid-fixture"
    if [ "$(stat -c '%u:%g:%a' "$fixture_helper")" != "$expected_mode" ]; then
        bbfatal "Synthetic SUID helper must be root:root with mode $expected_mode"
    fi
    cat ${IMAGE_ROOTFS}${datadir}/iotbench/dangerous-suid-rights/NOTICE >> ${IMAGE_ROOTFS}${sysconfdir}/motd
}
