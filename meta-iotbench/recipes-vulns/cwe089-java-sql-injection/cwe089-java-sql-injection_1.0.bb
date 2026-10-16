SUMMARY = "IoTBench fixture - CWE-89 SQL injection in Java JAR bytecode"
DESCRIPTION = "Intentionally insecure CLI/dashboard Java JDBC configuration lookup. SQL injection bypasses a public-visibility filter in a read-only synthetic SQLite database. Local lab testing only; not for deployment."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
SRC_URI = "file://LICENSE file://NOTICE file://FixtureDbQuery.java file://FixtureWebService.java file://schema.sql file://ground-truth.json file://test-guest.sh file://module.php file://iotbench-java-sql.service"
S = "${UNPACKDIR}"
DEPENDS = "openjdk-bin-native sqlite3-native"
RDEPENDS:${PN} = "openjdk iotbench-sqlite-jdbc busybox util-linux-setpriv router-dashboard"

inherit systemd useradd
SYSTEMD_SERVICE:${PN} = "iotbench-java-sql.service"
USERADD_PACKAGES = "${PN}"
GROUPADD_PARAM:${PN} = "--system --gid 990 javafixture"
USERADD_PARAM:${PN} = "--system --uid 990 --gid javafixture --home-dir /nonexistent --no-create-home --shell /sbin/nologin javafixture"

do_compile() {
    rm -rf ${B}/classes
    install -d ${B}/classes
    ${STAGING_LIBDIR_NATIVE}/jvm/bin/javac --release 17 -encoding UTF-8 -g \
        -Xlint:all -Werror -d ${B}/classes ${S}/FixtureDbQuery.java ${S}/FixtureWebService.java
    printf '%s\n' 'database.url=jdbc:sqlite:file:${datadir}/iotbench/java-sql-injection/fixture.db?mode=ro&immutable=1' \
        'driver.path=${libdir}' > ${B}/classes/fixture.properties
    rm -f ${B}/fixture.db
    sqlite3 -batch -bail ${B}/fixture.db < ${S}/schema.sql
}

# Fixed ZIP timestamps and ordering keep the executable JAR reproducible.
python do_package_jar() {
    import pathlib
    import zipfile
    classes = pathlib.Path(d.getVar('B')) / 'classes'
    manifest = ('Manifest-Version: 1.0\r\nMain-Class: org.iotbench.fixture.FixtureDbQuery\r\n'
                'Class-Path: ../../java/iotbench-sqlite-jdbc.jar\r\n\r\n')
    with zipfile.ZipFile(d.getVar('B') + '/fixture-db-query.jar', 'w') as jar:
        entries = [('META-INF/MANIFEST.MF', manifest.encode())]
        entries += [(p.relative_to(classes).as_posix(), p.read_bytes()) for p in sorted(classes.rglob('*')) if p.is_file()]
        for name, data in entries:
            info = zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            jar.writestr(info, data)
}
addtask package_jar after do_compile before do_install

do_install() {
    install -d ${D}${datadir}/iotbench/java-sql-injection
    install -m 0644 ${B}/fixture-db-query.jar ${D}${datadir}/iotbench/java-sql-injection/
    install -m 0444 ${B}/fixture.db ${D}${datadir}/iotbench/java-sql-injection/
    for fixture_file in LICENSE NOTICE FixtureDbQuery.java FixtureWebService.java schema.sql; do
        install -m 0644 ${S}/$fixture_file ${D}${datadir}/iotbench/java-sql-injection/
    done
    for fixture_file in ground-truth.json test-guest.sh; do
        sed -e 's|@DATADIR@|${datadir}|g' -e 's|@LIBDIR@|${libdir}|g' \
            ${S}/$fixture_file > ${D}${datadir}/iotbench/java-sql-injection/$fixture_file
        chmod 0644 ${D}${datadir}/iotbench/java-sql-injection/$fixture_file
    done
    install -d ${D}${datadir}/router-dashboard/modules/java-configuration-lookup ${D}${systemd_system_unitdir}
    install -m 0644 ${S}/module.php ${D}${datadir}/router-dashboard/modules/java-configuration-lookup/
    sed -e 's|@DATADIR@|${datadir}|g' -e 's|@BINDIR@|${bindir}|g' ${S}/iotbench-java-sql.service \
        > ${D}${systemd_system_unitdir}/iotbench-java-sql.service
}

FILES:${PN} = "${datadir}/iotbench/java-sql-injection ${datadir}/router-dashboard/modules/java-configuration-lookup ${systemd_system_unitdir}/iotbench-java-sql.service"
