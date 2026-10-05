require recipes-images/iotbench-image.inc
require recipes-devices/smartplug/device-smartplug.inc

SUMMARY = "IoTBench target - smart plug, CWE-78 MQTT command injection"
DESCRIPTION = "Smart plug firmware whose privileged relay-schedule agent interpolates an MQTT payload into a shell command."

IOTBENCH_CWE = "CWE-78"
IOTBENCH_VULN_INSTALL = "cwe078-mqtt-command-injection"
