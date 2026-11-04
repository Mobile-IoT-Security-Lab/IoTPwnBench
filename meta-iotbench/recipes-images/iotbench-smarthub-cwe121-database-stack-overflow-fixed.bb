require recipes-images/iotbench-image.inc
require recipes-devices/smarthub/device-smarthub.inc

SUMMARY = "IoTBench corrected twin - smart hub, CWE-121 database stack overflow"
DESCRIPTION = "Corrected twin of iotbench-smarthub-cwe121-database-stack-overflow. The same device and service, with the weakness removed. No weakness is injected."

IOTBENCH_CWE = "CWE-121"
IOTBENCH_VULN_INSTALL = "cwe121-smarthub-stack-overflow-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
