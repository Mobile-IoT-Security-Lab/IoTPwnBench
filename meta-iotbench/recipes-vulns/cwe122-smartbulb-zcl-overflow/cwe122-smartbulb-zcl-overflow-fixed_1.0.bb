require recipes-vulns/cwe122-smartbulb-zcl-overflow/cwe122-smartbulb-zcl-overflow_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-122 smart bulb ZCL heap overflow"
DESCRIPTION = "Corrected twin of cwe122-smartbulb-zcl-overflow. The frame length is checked against the 32-byte attribute value. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
