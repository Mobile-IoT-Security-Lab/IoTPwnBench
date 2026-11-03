require recipes-images/iotbench-image.inc
require recipes-devices/doorlock/device-doorlock.inc

SUMMARY = "IoTBench corrected twin - doorlock, CWE-276 anonymous FTP login allowed"
DESCRIPTION = "Corrected twin of iotbench-doorlock-cwe276-allow-anonymous-login. The same device and service, with the weakness removed. No weakness is injected."

IOTBENCH_CWE = "CWE-276"
IOTBENCH_VULN_INSTALL = "cwe276-allow-anonymous-login-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
