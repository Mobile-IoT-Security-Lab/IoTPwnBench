require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc
require recipes-images/iotbench-hardcoded-user-passwords.inc

SUMMARY = "IoTBench corrected twin - router, CWE-798 hardcoding user passwords"
DESCRIPTION = "Corrected twin of iotbench-router-cwe798-hardcoded-user-passwords. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_CWE = "CWE-798"
IOTBENCH_VULN_INSTALL = "cwe798-hardcoded-user-passwords-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
