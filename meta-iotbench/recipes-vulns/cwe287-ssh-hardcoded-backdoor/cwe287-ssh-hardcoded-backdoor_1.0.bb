SUMMARY = "IoTBench vulnerability module - CWE-287 SSH hardcoded backdoor"
DESCRIPTION = "Adds a hardcoded support account for SSH access. Intentionally vulnerable; lab use only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

inherit useradd

USERADD_PACKAGES = "${PN}"
USERADD_PARAM:${PN} = "--system --uid 996 --home-dir /home/support --create-home --shell /bin/sh --password '\$6\$iotbench\$EhBo2e24buhGDuzZQTBFBg58AJA3.wI.gOIVDU0A91zC8jaiqiIY//.WW6PfQB6Jf4qnaLLCU7BFkXvuKT1XG1' support"

RDEPENDS:${PN} = "router-dashboard dropbear"
ALLOW_EMPTY:${PN} = "1"
