require recipes-images/iotbench-image.inc
require recipes-devices/doorlock/device-doorlock.inc
require recipes-images/iotbench-coap-internal-files.inc

SUMMARY = "IoTBench corrected twin - doorlock, CWE-862 CoAP internal-file exposure"
DESCRIPTION = "Corrected twin of iotbench-doorlock-cwe862-coap-internal-files. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_CWE = "CWE-862"
IOTBENCH_VULN_INSTALL = "cwe862-coap-internal-files-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
