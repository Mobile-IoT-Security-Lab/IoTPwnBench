require recipes-images/iotbench-image.inc
require recipes-devices/smartbulb/device-smartbulb.inc
require recipes-images/iotbench-integer-overflow.inc

SUMMARY = "IoTBench corrected twin - smartbulb, CWE-190 native C integer overflow"
DESCRIPTION = "Corrected twin of iotbench-smartbulb-cwe190-integer-overflow. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_CWE = "CWE-190"
IOTBENCH_VULN_INSTALL = "cwe190-integer-overflow-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
