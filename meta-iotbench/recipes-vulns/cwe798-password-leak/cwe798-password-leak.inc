SUMMARY = "IoTBench synthetic CWE-798 password leak, ${IOTBENCH_PASSWORD_LEAK_VARIANT}"
DESCRIPTION = "One deterministic credential in one file type, consumed by local simulated authentication. Explicit research builds only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI = "file://LICENSE file://NOTICE file://fixture-build.py file://fixture-lib.py \
           file://fixture-auth.py file://fixture-auth.c file://synthetic-inventory.json \
           file://expected-findings.json file://fixtures file://negative"
S = "${UNPACKDIR}"

inherit python3native
RDEPENDS:${PN} = "python3-core python3-modules"
IOTBENCH_BUILD_MODE ?= "production"
IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE ?= "0"
FIXTURE_ROOT = "${datadir}/iotbench/password-leak/${IOTBENCH_PASSWORD_LEAK_VARIANT}"

python __anonymous() {
    import runpy
    policy = d.getVar('THISDIR') + '/files/fixture-lib.py'
    bb.parse.mark_dependency(d, policy)
    try:
        runpy.run_path(policy)['validate_build'](
            d.getVar('IOTBENCH_BUILD_MODE'),
            d.getVar('IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE'), d.getVar('MACHINE'),
            d.getVar('IOTBENCH_PASSWORD_LEAK_VARIANT'))
    except ValueError as error:
        raise bb.parse.SkipRecipe(str(error))
}

do_compile() {
    ${CC} ${CPPFLAGS} ${CFLAGS} -std=c11 -Wall -Wextra -Werror \
        -DIOTBENCH_FIXTURE_ROOT='"${FIXTURE_ROOT}"' \
        ${S}/fixture-auth.c ${LDFLAGS} -o ${B}/fixture-auth
}
do_install[vardeps] += "IOTBENCH_BUILD_MODE IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE MACHINE IOTBENCH_PASSWORD_LEAK_VARIANT"
do_install() {
    # Stage to a fresh tree, then copy only this scenario into the package.
    rm -rf ${B}/password-leak-stage
    ${PYTHON} ${S}/fixture-build.py --output ${B}/password-leak-stage \
        --variant '${IOTBENCH_PASSWORD_LEAK_VARIANT}' --datadir '${datadir}' \
        --mode '${IOTBENCH_BUILD_MODE}' --enable '${IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE}' \
        --machine '${MACHINE}'
    install -d ${D}${datadir}/iotbench/password-leak
    cp -R ${B}/password-leak-stage${FIXTURE_ROOT} ${D}${datadir}/iotbench/password-leak/
    install -m 0755 ${B}/fixture-auth ${D}${FIXTURE_ROOT}/fixture-auth
}

# One local native credential consumer only; no units, accounts or startup hooks.
FILES:${PN} = "${FIXTURE_ROOT}"
