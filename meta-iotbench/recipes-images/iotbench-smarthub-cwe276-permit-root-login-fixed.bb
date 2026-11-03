require recipes-images/iotbench-image.inc
require recipes-devices/smarthub/device-smarthub.inc

SUMMARY = "IoTBench corrected twin - smarthub, CWE-276 SSH root login permitted"
DESCRIPTION = "Corrected twin of iotbench-smarthub-cwe276-permit-root-login. The same device and service, with the weakness removed. No weakness is injected."

IOTBENCH_CWE = "CWE-276"
IOTBENCH_VULN_INSTALL = "cwe276-permit-root-login-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
