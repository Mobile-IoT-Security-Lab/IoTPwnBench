SUMMARY = "Opt-in synthetic Apache application fixture, CWE-${APACHE_FIXTURE_CWE}"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI = "file://LICENSE file://app.cgi file://httpd.conf.in file://isolate.c \
           file://fixture-build.py file://test-fixtures.py file://browser.py \
           file://variants/cwe${APACHE_FIXTURE_CWE}.py"
S = "${UNPACKDIR}"
IOTBENCH_BUILD_MODE ?= "production"
IOTBENCH_ENABLE_APACHE_FIXTURE ?= "0"
FIXTURE_BASE = "${datadir}/iotbench/apache-fixture"
RDEPENDS:${PN} = "apache2 python3-core python3-modules ldd"
inherit useradd
USERADD_PACKAGES = "${PN}"
USERADD_PARAM:${PN} = "--system --user-group --home /nonexistent --no-create-home --shell /bin/sh iotapache"

python __anonymous() {
    import runpy
    policy = d.getVar('THISDIR') + '/files/fixture-build.py'
    bb.parse.mark_dependency(d, policy)
    try:
        runpy.run_path(policy)['validate_build'](d.getVar('IOTBENCH_BUILD_MODE'),
            d.getVar('IOTBENCH_ENABLE_APACHE_FIXTURE'), d.getVar('MACHINE'))
    except ValueError as error:
        raise bb.parse.SkipRecipe(str(error))
}

do_compile() {
    ${CC} ${CPPFLAGS} ${CFLAGS} ${LDFLAGS} -std=c11 -Wall -Wextra -Werror \
        ${S}/isolate.c -o ${B}/isolate
}

do_install() {
    install -d ${D}${FIXTURE_BASE}
    for name in LICENSE app.cgi httpd.conf.in fixture-build.py test-fixtures.py browser.py; do
        install -m 0644 ${S}/$name ${D}${FIXTURE_BASE}/$name
    done
    install -m 0644 ${S}/variants/cwe${APACHE_FIXTURE_CWE}.py ${D}${FIXTURE_BASE}/scenario.py
    install -m 0755 ${B}/isolate ${D}${FIXTURE_BASE}/isolate
    printf '{"cwe":"%s"}\n' '${APACHE_FIXTURE_CWE}' > ${D}${FIXTURE_BASE}/variant.json
}
# No startup unit, default config include, setuid bit or added capability.
FILES:${PN} = "${FIXTURE_BASE}"
