require recipes-vulns/cwe416-use-after-free/cwe416-use-after-free_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-416 use after free"
DESCRIPTION = "Corrected twin of cwe416-use-after-free. The authorization object is freed after its last use. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
