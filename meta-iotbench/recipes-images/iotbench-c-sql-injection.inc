# Assert ordinary permissions and display the exact fixture warning at login.
ROOTFS_POSTPROCESS_COMMAND += "iotbench_c_sql_injection_metadata; "

iotbench_c_sql_injection_metadata() {
    fixture_data="${IMAGE_ROOTFS}${datadir}/iotbench/c-sql-injection"
    if [ "$(stat -c '%u:%g:%a' "${IMAGE_ROOTFS}${bindir}/fixture-db-query")" != "0:0:755" ]; then
        bbfatal "Native SQL fixture helper must be ordinary root:root 0755"
    fi
    if [ "$(stat -c '%u:%g:%a' "$fixture_data/fixture.db")" != "0:0:444" ]; then
        bbfatal "Synthetic SQLite database must be root:root 0444"
    fi
    cat "$fixture_data/NOTICE" >> ${IMAGE_ROOTFS}${sysconfdir}/motd
}
