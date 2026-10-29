SUMMARY = "IoTBench synthetic CWE-798 embedded authentication, ${IOTBENCH_EMBEDDED_AUTH_VARIANT}"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI = "file://LICENSE file://fixture-lib.py file://fixture-build.py \
           file://fixture-service.py file://fixture-test.py file://inventory.json file://fixtures"
S = "${UNPACKDIR}"
inherit python3native
RDEPENDS:${PN} = "python3-core python3-modules"
IOTBENCH_BUILD_MODE ?= "production"
IOTBENCH_ENABLE_EMBEDDED_AUTH_FIXTURE ?= "0"
FIXTURE_ROOT = "${datadir}/iotbench/embedded-auth/${IOTBENCH_EMBEDDED_AUTH_VARIANT}"

python __anonymous() {
    import runpy
    policy = d.getVar('THISDIR') + '/files/fixture-lib.py'
    bb.parse.mark_dependency(d, policy)
    try:
        runpy.run_path(policy)['validate_build'](
            d.getVar('IOTBENCH_BUILD_MODE'), d.getVar('IOTBENCH_ENABLE_EMBEDDED_AUTH_FIXTURE'),
            d.getVar('MACHINE'), d.getVar('IOTBENCH_EMBEDDED_AUTH_VARIANT'))
    except ValueError as error:
        raise bb.parse.SkipRecipe(str(error))
    if d.getVar('datadir') != '/usr/share':
        raise bb.parse.SkipRecipe('Embedded auth fixture requires the standard /usr/share datadir')
}

do_compile() {
    if [ '${IOTBENCH_EMBEDDED_AUTH_VARIANT}' = native ]; then
        # Keep the toolchain's CFLAGS/LDFLAGS and all normal security features.
        ${CC} ${CPPFLAGS} ${CFLAGS} -std=c11 -Wall -Wextra -Werror -fstack-protector-all -fPIC -shared \
            -DIOTBENCH_EMBEDDED_AUTH_ENABLED=1 ${S}/fixtures/native/credential.c \
            ${LDFLAGS} -Wl,-z,relro,-z,now,-z,noexecstack -o ${B}/credential.so
    fi
}

do_install[vardeps] += "IOTBENCH_BUILD_MODE IOTBENCH_ENABLE_EMBEDDED_AUTH_FIXTURE MACHINE IOTBENCH_EMBEDDED_AUTH_VARIANT"
do_install() {
    rm -rf ${B}/embedded-auth-stage
    if [ '${IOTBENCH_EMBEDDED_AUTH_VARIANT}' = native ]; then
        ${PYTHON} ${S}/fixture-build.py --output ${B}/embedded-auth-stage \
            --mode '${IOTBENCH_BUILD_MODE}' --enable '${IOTBENCH_ENABLE_EMBEDDED_AUTH_FIXTURE}' \
            --machine '${MACHINE}' --variant native --native-binary ${B}/credential.so
    else
        ${PYTHON} ${S}/fixture-build.py --output ${B}/embedded-auth-stage \
            --mode '${IOTBENCH_BUILD_MODE}' --enable '${IOTBENCH_ENABLE_EMBEDDED_AUTH_FIXTURE}' \
            --machine '${MACHINE}' --variant '${IOTBENCH_EMBEDDED_AUTH_VARIANT}'
    fi
    install -d ${D}${datadir}/iotbench/embedded-auth
    cp -R ${B}/embedded-auth-stage${FIXTURE_ROOT} ${D}${datadir}/iotbench/embedded-auth/
}

# This unversioned library is a private ctypes plugin, not a development link.
FILES_SOLIBSDEV = ""
FILES:${PN} = "${FIXTURE_ROOT}"
