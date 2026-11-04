require recipes-vulns/cwe121-smarthub-stack-overflow/cwe121-smarthub-stack-overflow_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-121 smart hub stack overflow"
DESCRIPTION = "Corrected twin of cwe121-smarthub-stack-overflow. The bucket name is copied with a bound. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
