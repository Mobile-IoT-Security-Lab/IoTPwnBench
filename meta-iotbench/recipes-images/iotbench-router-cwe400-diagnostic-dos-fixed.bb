require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench corrected twin - router, CWE-400 diagnostic denial of service"
DESCRIPTION = "Corrected twin of iotbench-router-cwe400-diagnostic-dos. The same device and service, with the weakness removed. No weakness is injected."

IOTBENCH_CWE = "CWE-400"
IOTBENCH_VULN_INSTALL = "cwe400-diagnostic-dos-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
