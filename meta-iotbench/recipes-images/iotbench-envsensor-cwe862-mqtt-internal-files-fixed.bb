require recipes-images/iotbench-image.inc
require recipes-devices/envsensor/device-envsensor.inc
require recipes-images/iotbench-mqtt-internal-files.inc

SUMMARY = "IoTBench corrected twin - envsensor, CWE-862 MQTT internal-file exposure"
DESCRIPTION = "Corrected twin of iotbench-envsensor-cwe862-mqtt-internal-files. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_CWE = "CWE-862"
IOTBENCH_VULN_INSTALL = "cwe862-mqtt-internal-files-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
