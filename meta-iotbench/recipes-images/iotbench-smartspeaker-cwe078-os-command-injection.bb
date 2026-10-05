require recipes-images/iotbench-image.inc
require recipes-devices/smartspeaker/device-smartspeaker.inc

SUMMARY = "IoTBench target - smart speaker, CWE-78 MQTT command injection"
DESCRIPTION = "Smart speaker firmware whose privileged media-source agent interpolates an MQTT payload into a shell command."

IOTBENCH_CWE = "CWE-78"
IOTBENCH_VULN_INSTALL = "cwe078-mqtt-command-injection"
