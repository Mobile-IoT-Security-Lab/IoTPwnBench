require recipes-vulns/cwe521-permit-empty-passwords/cwe521-permit-empty-passwords_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-521 permit empty passwords"
DESCRIPTION = "Corrected twin of cwe521-permit-empty-passwords. The SSH policy rejects empty passwords. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
