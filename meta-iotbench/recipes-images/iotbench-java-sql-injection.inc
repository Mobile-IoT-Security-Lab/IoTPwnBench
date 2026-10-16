ROOTFS_POSTPROCESS_COMMAND += "iotbench_java_sql_injection_metadata; "

iotbench_java_sql_injection_metadata() {
    fixture_data="${IMAGE_ROOTFS}${datadir}/iotbench/java-sql-injection"
    if [ "$(stat -c '%u:%g:%a' "$fixture_data/fixture-db-query.jar")" != "0:0:644" ]; then
        bbfatal "Java SQL fixture JAR must be ordinary root:root 0644"
    fi
    if [ "$(stat -c '%u:%g:%a' "$fixture_data/fixture.db")" != "0:0:444" ]; then
        bbfatal "Synthetic SQLite database must be root:root 0444"
    fi
    cat "$fixture_data/NOTICE" >> ${IMAGE_ROOTFS}${sysconfdir}/motd
}
