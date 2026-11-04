require recipes-vulns/cwe798-hardcoded-user-passwords/cwe798-hardcoded-user-passwords_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-798 hardcoded user passwords"
DESCRIPTION = "Corrected twin of cwe798-hardcoded-user-passwords. No account is shipped, the database is empty until a unique credential is enrolled. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"

do_install:append() {
    rm -f ${D}${datadir}/iotbench/*/test-guest.sh
}
