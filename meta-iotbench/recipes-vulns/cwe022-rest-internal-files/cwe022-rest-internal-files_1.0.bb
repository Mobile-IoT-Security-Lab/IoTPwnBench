SUMMARY = "IoTBench synthetic REST-to-internal-file traversal (CWE-22/CWE-73)"
DESCRIPTION = "One read-only path traversal scenario inside a dedicated synthetic filesystem; Unix socket only, explicit test builds only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
SRC_URI = "file://LICENSE file://NOTICE file://ground-truth.json \
           file://fixture-rest.c file://fixture-build.py file://assets"
S = "${UNPACKDIR}"
inherit python3native
DEPENDS += "virtual/libc"
RDEPENDS:${PN} = "curl"
IOTBENCH_BUILD_MODE ?= "production"
IOTBENCH_ENABLE_REST_FIXTURE ?= "0"
FIXTURE_BASE = "${datadir}/iotbench/rest-internal-files"

python __anonymous() {
    import runpy
    policy = d.getVar('THISDIR') + '/files/fixture-build.py'
    bb.parse.mark_dependency(d, policy)
    try:
        runpy.run_path(policy)['validate_build'](
            d.getVar('IOTBENCH_BUILD_MODE'),
            d.getVar('IOTBENCH_ENABLE_REST_FIXTURE'), d.getVar('MACHINE'))
    except ValueError as error:
        raise bb.parse.SkipRecipe(str(error))
}

do_compile[vardeps] += "IOTBENCH_BUILD_MODE IOTBENCH_ENABLE_REST_FIXTURE MACHINE"
do_compile() {
    ${CC} ${CPPFLAGS} ${CFLAGS} ${LDFLAGS} -std=c11 -Wall -Wextra -Werror \
        -DIOTBENCH_REST_FIXTURE_ENABLED=1 -DREST_SECURE_CONTROL=0 \
        -DFIXTURE_BASE='"${FIXTURE_BASE}"' \
        ${S}/fixture-rest.c -o ${B}/fixture-rest
    ${CC} ${CPPFLAGS} ${CFLAGS} ${LDFLAGS} -std=c11 -Wall -Wextra -Werror \
        -DIOTBENCH_REST_FIXTURE_ENABLED=1 -DREST_SECURE_CONTROL=1 \
        -DFIXTURE_BASE='"${FIXTURE_BASE}"' \
        ${S}/fixture-rest.c -o ${B}/fixture-rest-secure
}

do_install[vardeps] += "IOTBENCH_BUILD_MODE IOTBENCH_ENABLE_REST_FIXTURE MACHINE"
do_install() {
    ${PYTHON} ${S}/fixture-build.py --output ${D} --target-paths \
        --binary-dir ${B} --datadir '${datadir}' \
        --mode '${IOTBENCH_BUILD_MODE}' \
        --enable '${IOTBENCH_ENABLE_REST_FIXTURE}' --machine '${MACHINE}'
}

# No init script, service unit, network listener, setuid bit or capabilities.
FILES:${PN} = "${FIXTURE_BASE}"
