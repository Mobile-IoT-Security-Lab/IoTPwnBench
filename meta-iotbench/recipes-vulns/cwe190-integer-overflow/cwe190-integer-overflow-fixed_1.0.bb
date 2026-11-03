require recipes-vulns/cwe190-integer-overflow/cwe190-integer-overflow_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-190 integer overflow"
DESCRIPTION = "Corrected twin of cwe190-integer-overflow. The total is computed in 64 bits. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
