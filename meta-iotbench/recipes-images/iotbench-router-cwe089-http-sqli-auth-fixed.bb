require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench corrected twin - router, CWE-89 HTTP SQL injection"
DESCRIPTION = "Corrected twin of iotbench-router-cwe089-http-sqli-auth. The same device and service, with the weakness removed. No weakness is injected."

IOTBENCH_CWE = "CWE-89"
IOTBENCH_VULN_INSTALL = "cwe089-http-sqli-auth-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
