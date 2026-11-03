require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench corrected twin - router, CWE-22 path traversal"
DESCRIPTION = "Corrected twin of iotbench-router-cwe022-path-traversal. The same device and service, with the weakness removed. No weakness is injected."

IOTBENCH_CWE = "CWE-22"
IOTBENCH_VULN_INSTALL = "cwe022-path-traversal-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
