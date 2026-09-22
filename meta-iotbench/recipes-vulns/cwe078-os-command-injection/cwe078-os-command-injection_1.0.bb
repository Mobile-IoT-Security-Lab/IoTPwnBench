SUMMARY = "IoTBench vulnerability module - CWE-78 OS command injection"
DESCRIPTION = "Ping diagnostic dashboard module backed by a helper that builds a \
shell command from unsanitized input. Intentionally vulnerable; lab use only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"

SRC_URI = "file://LICENSE \
           file://router-ping.c \
           file://module.php \
           file://lighttpd-writable.conf"

S = "${UNPACKDIR}"

# Build the intentionally vulnerable helper from local C source.
DEPENDS += "virtual/libc"

# The module plugs into the dashboard and shells out to ping.
RDEPENDS:${PN} = "router-dashboard iputils-ping"

do_compile() {
    ${CC} ${CFLAGS} ${LDFLAGS} ${S}/router-ping.c -o ${B}/router-ping
}

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${B}/router-ping ${D}${bindir}/router-ping

    install -d ${D}${datadir}/router-dashboard/modules/ping
    install -m 0644 ${S}/module.php ${D}${datadir}/router-dashboard/modules/ping/module.php

    # Disable the upstream lighttpd systemd sandbox so the injected command can
    # write to the filesystem like a real RCE (still as the routerweb user).
    install -d ${D}${systemd_system_unitdir}/lighttpd.service.d
    install -m 0644 ${S}/lighttpd-writable.conf \
        ${D}${systemd_system_unitdir}/lighttpd.service.d/10-iotbench-writable.conf
}

FILES:${PN} = "${bindir}/router-ping \
               ${datadir}/router-dashboard/modules/ping \
               ${systemd_system_unitdir}/lighttpd.service.d"
