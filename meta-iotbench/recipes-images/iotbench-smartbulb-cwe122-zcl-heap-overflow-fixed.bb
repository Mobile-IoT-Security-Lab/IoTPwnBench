require recipes-images/iotbench-image.inc
require recipes-devices/smartbulb/device-smartbulb.inc

SUMMARY = "IoTBench corrected twin - smart bulb, CWE-122 ZCL heap overflow"
DESCRIPTION = "Corrected twin of iotbench-smartbulb-cwe122-zcl-heap-overflow. The same device and service, with the weakness removed. No weakness is injected."

IOTBENCH_CWE = "CWE-122"
IOTBENCH_VULN_INSTALL = "cwe122-smartbulb-zcl-overflow-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
