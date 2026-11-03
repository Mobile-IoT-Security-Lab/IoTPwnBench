# Preserve the synthetic account database and make the image warning visible.
ROOTFS_POSTPROCESS_COMMAND += "iotbench_hardcoded_user_passwords_metadata; "

iotbench_hardcoded_user_passwords_metadata() {
    fixture_accounts="${IMAGE_ROOTFS}${sysconfdir}/iotbench/hardcoded-user-passwords/accounts.conf"
    if [ "$(stat -c '%u:%g:%a' "$fixture_accounts")" != "0:0:600" ]; then
        bbfatal "Synthetic account database must be root:root with mode 0600"
    fi
    # A corrected twin installs an empty account database, see IOTBENCH_VULN_INSTALL.
    case "${IOTBENCH_VULN_INSTALL}" in
        *-fixed) reference="${THISDIR}/../recipes-vulns/cwe798-hardcoded-user-passwords/files-fixed/accounts.conf" ;;
        *) reference="${THISDIR}/../recipes-vulns/cwe798-hardcoded-user-passwords/files/accounts.conf" ;;
    esac
    if ! cmp -s "$fixture_accounts" "$reference"; then
        bbfatal "Synthetic user password must be installed verbatim in every firmware"
    fi
    fixture_helper="${IMAGE_ROOTFS}${bindir}/iotbench-fixture-auth"
    if [ "$(stat -c '%u:%g:%a' "$fixture_helper")" != "0:0:755" ]; then
        bbfatal "Local authentication helper must be ordinary root:root 0755"
    fi
    cat ${IMAGE_ROOTFS}${datadir}/iotbench/hardcoded-user-passwords/NOTICE >> ${IMAGE_ROOTFS}${sysconfdir}/motd
}
