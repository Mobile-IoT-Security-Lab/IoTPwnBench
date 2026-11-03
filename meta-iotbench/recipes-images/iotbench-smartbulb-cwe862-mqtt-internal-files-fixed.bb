require recipes-images/iotbench-image.inc
require recipes-devices/smartbulb/device-smartbulb.inc
require recipes-images/iotbench-mqtt-internal-files.inc

SUMMARY = "IoTBench corrected twin - smartbulb, CWE-862 MQTT internal-file exposure"
DESCRIPTION = "Corrected twin of iotbench-smartbulb-cwe862-mqtt-internal-files. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_CWE = "CWE-862"
IOTBENCH_VULN_INSTALL = "cwe862-mqtt-internal-files-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
