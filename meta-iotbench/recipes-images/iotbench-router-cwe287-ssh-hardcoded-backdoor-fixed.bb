require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench corrected twin - router, CWE-287 SSH hardcoded backdoor"
DESCRIPTION = "Corrected twin of iotbench-router-cwe287-ssh-hardcoded-backdoor. The same device and service, with the weakness removed. No weakness is injected."

IOTBENCH_CWE = "CWE-287"
IOTBENCH_VULN_INSTALL = "cwe287-ssh-hardcoded-backdoor-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
