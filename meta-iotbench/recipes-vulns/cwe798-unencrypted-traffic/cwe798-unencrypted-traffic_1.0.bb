SUMMARY = "IoTBench native Telnet maintenance login with plaintext traffic"
DESCRIPTION = "BusyBox telnetd and system login for an unprivileged maintenance account. Explicit test configuration and a private network namespace are required."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
SRC_URI = "file://LICENSE file://NOTICE file://ground-truth.json \
           file://fixture-build.py file://iotbench-telnet.service"
S = "${UNPACKDIR}"

inherit python3native features_check useradd
REQUIRED_DISTRO_FEATURES = "systemd"
RDEPENDS:${PN} = "busybox curl tcpdump util-linux-nsenter"
USERADD_PACKAGES = "${PN}"
GROUPADD_PARAM:${PN} = "--system maintenance"
# Public lab password: Maintenance-Telnet-42. Authentication uses /etc/shadow.
USERADD_PARAM:${PN} = "--system --gid maintenance --home-dir /var/lib/iotbench-telnet --no-create-home --shell /bin/sh --password '\$6\$iottelnet\$seLNm0ybp96oSLun4iJE8oBfwTPJQxvH9S7QIzdY7llykOcXia72auBk95NeFGFkjr2hJmiCMRjUOA/xl6ilX/' maintenance"
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
        --datadir '${datadir}' --unitdir '${systemd_system_unitdir}' --sbindir '${sbindir}'
    install -d -m 0755 ${D}/var/lib/iotbench-telnet
}

# No systemd inheritance/postinst enablement: unit has no [Install] section.
FILES:${PN} = "${datadir}/iotbench/unencrypted-traffic \
               ${systemd_system_unitdir}/iotbench-telnet.service /var/lib/iotbench-telnet"
