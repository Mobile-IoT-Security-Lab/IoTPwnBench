require recipes-images/iotbench-image.inc
require recipes-images/iotbench-bad-write-rights.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench corrected twin - router, CWE-276 vsftpd bad write rights"
IOTBENCH_CWE = "CWE-276"
IOTBENCH_VULN_INSTALL = "cwe276-bad-write-rights-fixed"
DESCRIPTION = "Corrected twin of iotbench-router-cwe276-bad-write-rights. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
