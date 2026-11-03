require recipes-images/iotbench-image.inc
require recipes-devices/healthmonitor/device-healthmonitor.inc
require recipes-images/iotbench-native-connection-string.inc

SUMMARY = "IoTBench corrected twin - healthmonitor, CWE-20 native C connection string injection"
DESCRIPTION = "Corrected twin of iotbench-healthmonitor-cwe020-native-connection-string. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_CWE = "CWE-20"
IOTBENCH_VULN_INSTALL = "cwe020-native-connection-string-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
