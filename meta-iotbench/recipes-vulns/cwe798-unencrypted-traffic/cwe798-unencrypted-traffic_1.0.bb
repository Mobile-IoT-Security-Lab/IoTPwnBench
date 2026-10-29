SUMMARY = "IoTBench synthetic weak Telnet with unencrypted traffic (CWE-798/287/276)"
DESCRIPTION = "One intentionally insecure synthetic Telnet scenario, loopback only, no operating-system shell."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
SRC_URI = "file://LICENSE file://NOTICE file://ground-truth.json file://fixture-telnet.py \
           file://fixture-build.py file://telnet-auth.json file://iotbench-telnet.service file://test-session.py"
S = "${UNPACKDIR}"

inherit python3native features_check
REQUIRED_DISTRO_FEATURES = "systemd"
RDEPENDS:${PN} = "python3-core python3-modules"
IOTBENCH_BUILD_MODE ?= "production"
IOTBENCH_ENABLE_TELNET_FIXTURE ?= "0"

# Removing the provider also prevents accidental installation from a cached
# fixture package into production images. The opt-in must be global test config.
python __anonymous() {
    import runpy
    policy = d.getVar('THISDIR') + '/files/fixture-build.py'
    bb.parse.mark_dependency(d, policy)
    validate = runpy.run_path(policy)['validate_build']
    try:
        validate(d.getVar('IOTBENCH_BUILD_MODE'),
                 d.getVar('IOTBENCH_ENABLE_TELNET_FIXTURE'), d.getVar('MACHINE'))
    except ValueError as error:
        raise bb.parse.SkipRecipe(str(error))
}

do_compile[noexec] = "1"
do_install[vardeps] += "IOTBENCH_BUILD_MODE IOTBENCH_ENABLE_TELNET_FIXTURE MACHINE"
do_install() {
    ${PYTHON} ${S}/fixture-build.py --target-paths --output ${D} \
        --mode '${IOTBENCH_BUILD_MODE}' --enable '${IOTBENCH_ENABLE_TELNET_FIXTURE}' \
        --machine '${MACHINE}' --bindir '${bindir}' --sysconfdir '${sysconfdir}' \
        --datadir '${datadir}' --unitdir '${systemd_system_unitdir}'
}

# No systemd inheritance/postinst enablement: unit has no [Install] section.
FILES:${PN} = "${bindir}/fixture-telnet ${sysconfdir}/iotbench/telnet-auth.json \
               ${datadir}/iotbench/unencrypted-traffic ${systemd_system_unitdir}/iotbench-telnet.service"
