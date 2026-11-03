require recipes-vulns/cwe022-bad-sudo-rights/cwe022-bad-sudo-rights_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-22 bad sudo rights"
DESCRIPTION = "Corrected twin of cwe022-bad-sudo-rights. The helper rejects dot components, so the data/ boundary holds. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
