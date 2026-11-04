require recipes-vulns/cwe862-coap-internal-files/cwe862-coap-internal-files_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-862 CoAP internal files"
DESCRIPTION = "Corrected twin of cwe862-coap-internal-files. Only a client on the device itself can read the internal files. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
