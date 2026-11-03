require recipes-vulns/cwe798-unencrypted-traffic/cwe798-unencrypted-traffic_1.0.bb

SUMMARY = "IoTBench corrected variant - unencrypted traffic, CWE-319/CWE-798"
DESCRIPTION = "Corrected twin of the Telnet maintenance fixture. No cleartext service is installed and the maintenance account is locked. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"

# The cleartext unit is not installed and the account has no usable password.
USERADD_PARAM:${PN} = "--system --gid maintenance --home-dir /var/lib/iotbench-telnet --no-create-home --shell /bin/sh --password '!' maintenance"
FILES:${PN} = "${datadir}/iotbench/unencrypted-traffic /var/lib/iotbench-telnet"
