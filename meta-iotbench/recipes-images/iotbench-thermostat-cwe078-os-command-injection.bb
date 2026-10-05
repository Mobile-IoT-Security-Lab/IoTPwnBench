require recipes-images/iotbench-image.inc
require recipes-devices/thermostat/device-thermostat.inc

SUMMARY = "IoTBench target - thermostat, CWE-78 MQTT command injection"
DESCRIPTION = "Thermostat firmware whose privileged HVAC-profile agent interpolates an MQTT payload into a shell command."

IOTBENCH_CWE = "CWE-78"
IOTBENCH_VULN_INSTALL = "cwe078-mqtt-command-injection"
