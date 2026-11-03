require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench corrected twin - router, CWE-78 OS command injection (ping diagnostic)"
DESCRIPTION = "Corrected twin of iotbench-router-cwe078-os-command-injection. The same device and service, with the weakness removed. No weakness is injected."

IOTBENCH_CWE = "CWE-78"
IOTBENCH_VULN_INSTALL = "cwe078-os-command-injection-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
