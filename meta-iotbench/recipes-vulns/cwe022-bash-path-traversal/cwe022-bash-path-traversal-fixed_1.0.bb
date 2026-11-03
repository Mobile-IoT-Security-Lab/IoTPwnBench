require recipes-vulns/cwe022-bash-path-traversal/cwe022-bash-path-traversal_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-22 Bash path traversal"
DESCRIPTION = "Corrected twin of cwe022-bash-path-traversal. Only a plain file name below data/ is accepted. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
