require recipes-images/iotbench-image.inc
require recipes-devices/doorlock/device-doorlock.inc
require recipes-images/iotbench-native-connection-string.inc

SUMMARY = "IoTBench corrected twin - doorlock, CWE-20 native C connection string injection"
DESCRIPTION = "Corrected twin of iotbench-doorlock-cwe020-native-connection-string. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_CWE = "CWE-20"
IOTBENCH_VULN_INSTALL = "cwe020-native-connection-string-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
