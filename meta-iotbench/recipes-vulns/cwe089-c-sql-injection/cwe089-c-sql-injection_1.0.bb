SUMMARY = "IoTBench fixture - CWE-89 SQL injection in a native C binary"
DESCRIPTION = "Intentionally insecure local synthetic SQLite lookup; argv[1] reaches SQL syntax in a native firmware executable. Local testing only; not for deployment."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
SRC_URI = "file://LICENSE file://fixture-db-query.c file://schema.sql file://NOTICE file://ground-truth.json file://test-guest.sh"
S = "${UNPACKDIR}"
DEPENDS = "sqlite3 sqlite3-native"
RDEPENDS:${PN} = "busybox util-linux-setpriv"

do_compile() {
    ${CC} ${CPPFLAGS} ${CFLAGS} ${LDFLAGS} -Wall -Wextra -Werror \
        -DFIXTURE_DB_PATH='"${datadir}/iotbench/c-sql-injection/fixture.db"' \
        ${S}/fixture-db-query.c -o ${B}/fixture-db-query -lsqlite3
    # Recreate from the same ordered inputs, never from an existing database.
    rm -f ${B}/fixture.db
    sqlite3 -batch -bail ${B}/fixture.db < ${S}/schema.sql
}

do_install() {
    install -d ${D}${bindir} ${D}${datadir}/iotbench/c-sql-injection
    install -m 0755 ${B}/fixture-db-query ${D}${bindir}/fixture-db-query
    install -m 0444 ${B}/fixture.db ${D}${datadir}/iotbench/c-sql-injection/fixture.db
    for fixture_file in LICENSE NOTICE fixture-db-query.c schema.sql; do
        install -m 0644 ${S}/$fixture_file ${D}${datadir}/iotbench/c-sql-injection/$fixture_file
    done
    for fixture_file in ground-truth.json test-guest.sh; do
        sed -e 's|@DATADIR@|${datadir}|g' -e 's|@BINDIR@|${bindir}|g' \
            -e 's|@SYSCONFDIR@|${sysconfdir}|g' ${S}/$fixture_file \
            > ${D}${datadir}/iotbench/c-sql-injection/$fixture_file
        chmod 0644 ${D}${datadir}/iotbench/c-sql-injection/$fixture_file
    done
}

FILES:${PN} = "${bindir}/fixture-db-query ${datadir}/iotbench/c-sql-injection"
