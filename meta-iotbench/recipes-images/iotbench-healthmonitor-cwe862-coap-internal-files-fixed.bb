require recipes-images/iotbench-image.inc
require recipes-devices/healthmonitor/device-healthmonitor.inc
require recipes-images/iotbench-coap-internal-files.inc

SUMMARY = "IoTBench corrected twin - healthmonitor, CWE-862 CoAP internal-file exposure"
DESCRIPTION = "Corrected twin of iotbench-healthmonitor-cwe862-coap-internal-files. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_CWE = "CWE-862"
IOTBENCH_VULN_INSTALL = "cwe862-coap-internal-files-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
