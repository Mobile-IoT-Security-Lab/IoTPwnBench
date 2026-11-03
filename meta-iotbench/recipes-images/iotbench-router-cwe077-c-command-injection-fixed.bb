require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench corrected twin - router, CWE-77 C command injection"
DESCRIPTION = "Corrected twin of iotbench-router-cwe077-c-command-injection. The same device and service, with the weakness removed. No weakness is injected."

IOTBENCH_CWE = "CWE-77"
IOTBENCH_VULN_INSTALL = "cwe077-c-command-injection-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
