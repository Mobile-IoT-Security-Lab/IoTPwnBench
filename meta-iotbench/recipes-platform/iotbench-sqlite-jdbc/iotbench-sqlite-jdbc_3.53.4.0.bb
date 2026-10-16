SUMMARY = "Pinned SQLite JDBC classes with a Yocto-built JNI library"
HOMEPAGE = "https://github.com/xerial/sqlite-jdbc"
LICENSE = "Apache-2.0 & BSD-2-Clause"
LIC_FILES_CHKSUM = "file://LICENSE;md5=d273d63619c9aeaf15cdaf76422c4f87 file://LICENSE.zentus;md5=d393760bd738a58c439f0a8eb5305d1b"
SRC_URI = "git://github.com/xerial/sqlite-jdbc;protocol=https;branch=master;tag=${PV} \
           https://repo.maven.apache.org/maven2/org/xerial/sqlite-jdbc/${PV}/sqlite-jdbc-${PV}.jar;name=jar;unpack=0"
SRCREV = "cab7981c19ce04d691f0675f0b2586afc2bbf803"
SRC_URI[jar.sha256sum] = "bcb1f51e36f940867e83342f9efbf5968ac44a6bef4d397bb4af7b17b45cd2fb"
DEPENDS = "openjdk-bin-native sqlite3"
RDEPENDS:${PN} = "openjdk"

do_compile() {
    install -d ${B}/headers ${B}/classes
    ${STAGING_LIBDIR_NATIVE}/jvm/bin/javac \
        -cp ${UNPACKDIR}/sqlite-jdbc-${PV}.jar -h ${B}/headers -d ${B}/classes \
        ${S}/src/main/java/org/sqlite/core/NativeDB.java
    cp ${B}/headers/org_sqlite_core_NativeDB.h ${B}/headers/NativeDB.h
    ${CC} ${CPPFLAGS} ${CFLAGS} ${LDFLAGS} -fPIC -shared \
        -I${STAGING_LIBDIR_NATIVE}/jvm/include -I${STAGING_LIBDIR_NATIVE}/jvm/include/linux \
        -I${B}/headers ${S}/src/main/java/org/sqlite/core/NativeDB.c \
        -o ${B}/libsqlitejdbc.so -lsqlite3
}

# Remove every bundled foreign native binary. The only JNI library shipped is
# compiled by Yocto for the selected target and uses its existing SQLite recipe.
python do_filter_jar() {
    import zipfile
    source = d.getVar('UNPACKDIR') + '/sqlite-jdbc-' + d.getVar('PV') + '.jar'
    target = d.getVar('B') + '/iotbench-sqlite-jdbc.jar'
    with zipfile.ZipFile(source) as src, zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as dst:
        for name in sorted(src.namelist()):
            if name.endswith('/') or name.startswith('org/sqlite/native/'):
                continue
            info = zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            dst.writestr(info, src.read(name))
}
addtask filter_jar after do_compile before do_install

do_install() {
    install -d ${D}${datadir}/java ${D}${libdir} ${D}${datadir}/licenses/${PN}
    install -m 0644 ${B}/iotbench-sqlite-jdbc.jar ${D}${datadir}/java/
    install -m 0755 ${B}/libsqlitejdbc.so ${D}${libdir}/
    install -m 0644 ${S}/LICENSE ${S}/LICENSE.zentus ${D}${datadir}/licenses/${PN}/
}

FILES:${PN} = "${datadir}/java/iotbench-sqlite-jdbc.jar ${libdir}/libsqlitejdbc.so ${datadir}/licenses/${PN}"
FILES:${PN}-dev = ""
