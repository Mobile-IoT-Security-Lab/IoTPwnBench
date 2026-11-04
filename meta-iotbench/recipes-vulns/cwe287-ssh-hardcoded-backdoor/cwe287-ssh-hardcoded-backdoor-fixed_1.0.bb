SUMMARY = "IoTBench corrected variant - CWE-287 SSH hardcoded backdoor"
DESCRIPTION = "Corrected twin of cwe287-ssh-hardcoded-backdoor. No undocumented support account is created. No weakness is injected."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

RDEPENDS:${PN} = "router-dashboard dropbear"
ALLOW_EMPTY:${PN} = "1"
