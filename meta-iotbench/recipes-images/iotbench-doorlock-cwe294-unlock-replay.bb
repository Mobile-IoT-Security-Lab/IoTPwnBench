require recipes-images/iotbench-image.inc
require recipes-devices/doorlock/device-doorlock.inc

SUMMARY = "IoTBench target - door lock, CWE-294 unlock replay"
DESCRIPTION = "Door lock firmware that accepts a captured authenticated unlock frame more than once."

IOTBENCH_CWE = "CWE-294"
IOTBENCH_VULN_INSTALL = "cwe294-mqtt-replay"
