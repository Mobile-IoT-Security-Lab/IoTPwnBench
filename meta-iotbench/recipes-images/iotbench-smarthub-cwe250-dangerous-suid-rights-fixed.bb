require recipes-images/iotbench-image.inc
require recipes-images/iotbench-dangerous-suid-rights.inc
require recipes-devices/smarthub/device-smarthub.inc

SUMMARY = "IoTBench corrected twin - smarthub, CWE-250 dangerous SUID rights"
IOTBENCH_CWE = "CWE-250"
IOTBENCH_VULN_INSTALL = "cwe250-dangerous-suid-rights-fixed"
DESCRIPTION = "Corrected twin of iotbench-smarthub-cwe250-dangerous-suid-rights. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
