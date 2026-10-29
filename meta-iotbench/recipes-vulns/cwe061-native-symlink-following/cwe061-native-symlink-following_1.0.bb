SUMMARY = "Opt-in native UNIX symlink following fixture (CWE-61, broader CWE-59)"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
# The existing native path launcher copies files into tmpfs and detaches host mounts.
FILESEXTRAPATHS:prepend := "${THISDIR}/files:${THISDIR}/../native-path-fixture/files:"
SRC_URI = "file://LICENSE file://NOTICE file://ground-truth.json \
           file://fixture-symlink.c file://isolate-path.c file://fixture-build.py \
           file://fixture-runner.py file://test-session.py file://assets"
S = "${UNPACKDIR}"
inherit python3native useradd
IOTBENCH_BUILD_MODE ?= "production"
IOTBENCH_ENABLE_NATIVE_SYMLINK_FIXTURE ?= "0"
FIXTURE_BASE = "${datadir}/iotbench/native-symlink"
CFLAGS:append = " -fstack-protector-strong -fPIE"
LDFLAGS:append = " -pie -Wl,-z,relro,-z,now,-z,noexecstack"
RDEPENDS:${PN} = "python3-core python3-modules ldd"
USERADD_PACKAGES = "${PN}"
USERADD_PARAM:${PN} = "--system --user-group --home /nonexistent --no-create-home --shell /bin/sh iotsymlink"

python __anonymous() {
    import runpy
    policy = d.getVar('THISDIR') + '/files/fixture-build.py'
    bb.parse.mark_dependency(d, policy)
    try:
        runpy.run_path(policy)['validate_build'](d.getVar('IOTBENCH_BUILD_MODE'),
            d.getVar('IOTBENCH_ENABLE_NATIVE_SYMLINK_FIXTURE'), d.getVar('MACHINE'))
    except ValueError as error:
        raise bb.parse.SkipRecipe(str(error))
}

do_compile[vardeps] += "IOTBENCH_BUILD_MODE IOTBENCH_ENABLE_NATIVE_SYMLINK_FIXTURE MACHINE"
do_compile() {
    ${CC} ${CPPFLAGS} ${CFLAGS} ${LDFLAGS} -std=c11 -Wall -Wextra -Werror \
        -DIOTBENCH_SYMLINK_FIXTURE_ENABLED=1 ${S}/fixture-symlink.c -o ${B}/fixture-symlink-cwe061
    ${CC} ${CPPFLAGS} ${CFLAGS} ${LDFLAGS} -std=c11 -Wall -Wextra -Werror \
        ${S}/isolate-path.c -o ${B}/isolate-path
}

do_install[vardeps] += "IOTBENCH_BUILD_MODE IOTBENCH_ENABLE_NATIVE_SYMLINK_FIXTURE MACHINE"
do_install() {
    ${PYTHON} ${S}/fixture-build.py --output ${D} --binary-dir ${B} --datadir '${datadir}' \
        --mode '${IOTBENCH_BUILD_MODE}' --enable '${IOTBENCH_ENABLE_NATIVE_SYMLINK_FIXTURE}' \
        --machine '${MACHINE}'
}

# Manual test runner only; no startup unit, setuid bits or capabilities.
FILES:${PN} = "${FIXTURE_BASE}"
INHIBIT_PACKAGE_STRIP = "1"
INHIBIT_PACKAGE_DEBUG_SPLIT = "1"
