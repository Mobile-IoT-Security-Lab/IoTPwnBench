SUMMARY = "IoTBench native sudo maintenance report with environment-sensitive units"
DESCRIPTION = "Real BusyBox du measures installed device configuration files. A preserved POSIXLY_CORRECT changes implicit reporting units; explicit -k is the control. Explicit QEMU lab builds only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
SRC_URI = "file://LICENSE file://NOTICE file://ground-truth.json file://iotbench-sudo-environment"
S = "${UNPACKDIR}"

inherit useradd
RDEPENDS:${PN} = "sudo busybox"
USERADD_PACKAGES = "${PN}"
GROUPADD_PARAM:${PN} = "--system --gid 989 fixtureenv"
USERADD_PARAM:${PN} = "--system --uid 989 --gid fixtureenv --home-dir /nonexistent --no-create-home --shell /bin/false --password '!' fixtureenv"
IOTBENCH_BUILD_MODE ?= "production"
IOTBENCH_ENABLE_SUDO_ENV_FIXTURE ?= "0"

python __anonymous() {
    if (d.getVar('IOTBENCH_BUILD_MODE') != 'fixture' or
            d.getVar('IOTBENCH_ENABLE_SUDO_ENV_FIXTURE') != '1' or
            d.getVar('MACHINE') not in ('qemuarm64', 'qemuarm', 'qemux86-64', 'qemux86', 'qemumips')):
        raise bb.parse.SkipRecipe('Native sudo maintenance report requires explicit fixture mode, its opt-in, and a supported QEMU machine')
}

do_compile[noexec] = "1"
do_install() {
    install -d ${D}${sysconfdir}/sudoers.d ${D}${datadir}/iotbench/sudo-environment
    sed 's|@BASE_BINDIR@|${base_bindir}|g' ${S}/iotbench-sudo-environment \
        > ${D}${sysconfdir}/sudoers.d/iotbench-sudo-environment
    chmod 0440 ${D}${sysconfdir}/sudoers.d/iotbench-sudo-environment
    install -m 0644 ${S}/NOTICE ${S}/LICENSE ${S}/ground-truth.json \
        ${D}${datadir}/iotbench/sudo-environment/
}

FILES:${PN} = "${sysconfdir}/sudoers.d/iotbench-sudo-environment ${datadir}/iotbench/sudo-environment"
