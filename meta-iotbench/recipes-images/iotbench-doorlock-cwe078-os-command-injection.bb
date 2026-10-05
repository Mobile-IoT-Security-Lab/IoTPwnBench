require recipes-images/iotbench-image.inc
require recipes-devices/doorlock/device-doorlock.inc

SUMMARY = "IoTBench target - door lock, CWE-78 MQTT command injection"
DESCRIPTION = "Door lock firmware whose privileged firmware-update agent interpolates an MQTT payload into a shell command."

IOTBENCH_CWE = "CWE-78"
IOTBENCH_VULN_INSTALL = "cwe078-mqtt-command-injection"
