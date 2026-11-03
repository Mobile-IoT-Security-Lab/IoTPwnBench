require recipes-vulns/cwe798-ld-preload-sudo/cwe798-ld-preload-sudo_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-798 LD_PRELOAD sudo rule"
DESCRIPTION = "Corrected twin of cwe798-ld-preload-sudo. The sudo rule does not keep LD_PRELOAD and does not allow setting the environment. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
