SUMMARY = "IoTBench synthetic bad sudo environment policy (CWE-798)"
DESCRIPTION = "One local synthetic sudo workflow: selected environment settings and a public fixed diagnostic credential. Explicit QEMU test builds only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
SRC_URI = "file://LICENSE file://NOTICE file://ground-truth.json file://fixture-sudo-env.c \
           file://fixture-build.py file://iotbench-sudo-environment file://test-session.py"
S = "${UNPACKDIR}"

inherit useradd python3native
DEPENDS += "virtual/libc"
RDEPENDS:${PN} = "sudo python3-core python3-modules"
USERADD_PACKAGES = "${PN}"
GROUPADD_PARAM:${PN} = "--system --gid 989 fixtureenv"
USERADD_PARAM:${PN} = "--system --uid 989 --gid fixtureenv --home-dir /nonexistent --no-create-home --shell /bin/false --password '!' fixtureenv"
IOTBENCH_BUILD_MODE ?= "production"
IOTBENCH_ENABLE_SUDO_ENV_FIXTURE ?= "0"
FIXTURE_ROOT = "${datadir}/iotbench/sudo-environment"

# A global test configuration is required even to provide this package.
python __anonymous() {
    import runpy
    policy = d.getVar('THISDIR') + '/files/fixture-build.py'
    bb.parse.mark_dependency(d, policy)
    validate = runpy.run_path(policy)['validate_build']
    try:
        validate(d.getVar('IOTBENCH_BUILD_MODE'),
                 d.getVar('IOTBENCH_ENABLE_SUDO_ENV_FIXTURE'), d.getVar('MACHINE'))
    except ValueError as error:
        raise bb.parse.SkipRecipe(str(error))
}

do_compile[vardeps] += "IOTBENCH_BUILD_MODE IOTBENCH_ENABLE_SUDO_ENV_FIXTURE MACHINE"
do_compile() {
    ${CC} ${CFLAGS} ${LDFLAGS} -std=c11 -Wall -Wextra -Werror \
        -DIOTBENCH_SUDO_ENV_FIXTURE_ENABLED=1 \
        -DFIXTURE_MANIFEST='"${FIXTURE_ROOT}/build-config"' \
        ${S}/fixture-sudo-env.c -o ${B}/fixture-sudo-env
}

do_install[vardeps] += "IOTBENCH_BUILD_MODE IOTBENCH_ENABLE_SUDO_ENV_FIXTURE MACHINE"
do_install() {
    ${PYTHON} ${S}/fixture-build.py --output ${D} --target-paths \
        --binary ${B}/fixture-sudo-env --mode '${IOTBENCH_BUILD_MODE}' \
        --enable '${IOTBENCH_ENABLE_SUDO_ENV_FIXTURE}' --machine '${MACHINE}' \
        --bindir '${bindir}' --base-bindir '${base_bindir}' \
        --sysconfdir '${sysconfdir}' --datadir '${datadir}'
}

# No service, startup links, setuid helper or network listener.
FILES:${PN} = "${bindir}/fixture-sudo-env ${sysconfdir}/sudoers.d/iotbench-sudo-environment ${FIXTURE_ROOT}"
