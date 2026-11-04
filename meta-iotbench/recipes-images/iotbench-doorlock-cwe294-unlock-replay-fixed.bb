require recipes-images/iotbench-image.inc
require recipes-devices/doorlock/device-doorlock.inc

SUMMARY = "IoTBench corrected twin - door lock, CWE-294 unlock replay"
DESCRIPTION = "Corrected twin of iotbench-doorlock-cwe294-unlock-replay. The same device and service, with the weakness removed. No weakness is injected."

IOTBENCH_CWE = "CWE-294"
IOTBENCH_VULN_INSTALL = "cwe294-mqtt-replay-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
