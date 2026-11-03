require recipes-vulns/cwe476-null-pointer-dereference/cwe476-null-pointer-dereference_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-476 native C null pointer dereference"
DESCRIPTION = "Corrected twin of cwe476-null-pointer-dereference. The lookup result is checked before use. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
