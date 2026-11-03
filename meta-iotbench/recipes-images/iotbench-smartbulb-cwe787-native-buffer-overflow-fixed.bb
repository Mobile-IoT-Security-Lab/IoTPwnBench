require recipes-images/iotbench-image.inc
require recipes-devices/smartbulb/device-smartbulb.inc
require recipes-images/iotbench-native-buffer-overflow.inc

SUMMARY = "IoTBench corrected twin - smartbulb, CWE-787 native C buffer overflow"
DESCRIPTION = "Corrected twin of iotbench-smartbulb-cwe787-native-buffer-overflow. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_CWE = "CWE-787"
IOTBENCH_VULN_INSTALL = "cwe787-native-buffer-overflow-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
