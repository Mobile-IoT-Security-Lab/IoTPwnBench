SUMMARY = "Opt-in native filesystem path fixture, CWE-${PATH_FIXTURE_CWE}"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI = "file://LICENSE file://NOTICE file://ground-truth.json \
           file://fixture-path.c file://isolate-path.c file://fixture-build.py \
           file://fixture-runner.py file://test-session.py file://assets"
S = "${UNPACKDIR}"
inherit python3native useradd
IOTBENCH_BUILD_MODE ?= "production"
IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE ?= "0"
FIXTURE_BASE = "${datadir}/iotbench/native-path"
# Opt in to sanitizer builds on targets providing libasan/libubsan.
PACKAGECONFIG ??= ""
PACKAGECONFIG[asan] = ",,,,"
# Add protections without replacing the distribution's normal compiler flags.
CFLAGS:append = " -fstack-protector-strong -fPIE"
LDFLAGS:append = " -pie -Wl,-z,relro,-z,now,-z,noexecstack"
RDEPENDS:${PN} = "python3-core python3-modules ldd"
USERADD_PACKAGES = "${PN}"
USERADD_PARAM:${PN} = "--system --user-group --home /nonexistent --no-create-home --shell /bin/sh iotpath"

python __anonymous() {
    import runpy
    policy = d.getVar('THISDIR') + '/files/fixture-build.py'
    bb.parse.mark_dependency(d, policy)
    try:
        runpy.run_path(policy)['validate_build'](d.getVar('IOTBENCH_BUILD_MODE'),
            d.getVar('IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE'), d.getVar('MACHINE'))
    except ValueError as error:
        raise bb.parse.SkipRecipe(str(error))
}

do_compile[vardeps] += "IOTBENCH_BUILD_MODE IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE MACHINE PATH_FIXTURE_CWE"
do_compile() {
    # The normal fixture ELF runs after isolate-path pivots into a deliberately
    # minimal tmpfs root. Link that actual request handler as static PIE so a
    # researcher can exercise it manually there without staging a guest loader
    # or a Python runtime. The optional ASan diagnostic remains dynamically
    # linked and is used only by the existing regression runner.
    ${CC} ${CPPFLAGS} ${CFLAGS} ${LDFLAGS} -std=c11 -Wall -Wextra -Werror \
        -static-pie \
        -DIOTBENCH_PATH_FIXTURE_ENABLED=1 -DPATH_FIXTURE_CWE=${@int(d.getVar('PATH_FIXTURE_CWE'))} \
        ${S}/fixture-path.c -o ${B}/fixture-path-cwe${PATH_FIXTURE_CWE}
    ${CC} ${CPPFLAGS} ${CFLAGS} ${LDFLAGS} -std=c11 -Wall -Wextra -Werror \
        ${S}/isolate-path.c -o ${B}/isolate-path
    if ${@'true' if bb.utils.contains('PACKAGECONFIG', 'asan', True, False, d) else 'false'}; then
        ${CC} ${CPPFLAGS} ${CFLAGS} ${LDFLAGS} -std=c11 -Wall -Wextra -Werror \
            -DIOTBENCH_PATH_FIXTURE_ENABLED=1 -DPATH_FIXTURE_CWE=${@int(d.getVar('PATH_FIXTURE_CWE'))} \
            -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer \
            ${S}/fixture-path.c -o ${B}/fixture-path-cwe${PATH_FIXTURE_CWE}-asan
    fi
}

do_install[vardeps] += "IOTBENCH_BUILD_MODE IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE MACHINE PATH_FIXTURE_CWE"
do_install() {
    ${PYTHON} ${S}/fixture-build.py --output ${D} --binary-dir ${B} --datadir '${datadir}' \
        --cwe '${PATH_FIXTURE_CWE}' --mode '${IOTBENCH_BUILD_MODE}' \
        --enable '${IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE}' --machine '${MACHINE}' \
        ${@bb.utils.contains('PACKAGECONFIG', 'asan', '--sanitize', '', d)}
}

# No startup unit, listener, setuid bit or file capabilities.
FILES:${PN} = "${FIXTURE_BASE}"
# The artifact manifest hashes installed ELF bytes. Retain those exact bytes
# through packaging, including symbols useful to firmware analysis tools.
INHIBIT_PACKAGE_STRIP = "1"
INHIBIT_PACKAGE_DEBUG_SPLIT = "1"
