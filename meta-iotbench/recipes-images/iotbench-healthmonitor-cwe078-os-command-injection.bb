require recipes-images/iotbench-image.inc
require recipes-devices/healthmonitor/device-healthmonitor.inc

SUMMARY = "IoTBench target - health monitor, CWE-78 MQTT command injection"
DESCRIPTION = "Health monitor firmware whose privileged export-target agent interpolates an MQTT payload into a shell command."

IOTBENCH_CWE = "CWE-78"
IOTBENCH_VULN_INSTALL = "cwe078-mqtt-command-injection"
