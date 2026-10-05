require recipes-images/iotbench-image.inc
require recipes-devices/thermostat/device-thermostat.inc

SUMMARY = "IoTBench target - thermostat, CWE-294 command replay"
DESCRIPTION = "Thermostat firmware that accepts a captured authenticated setpoint frame more than once."

IOTBENCH_CWE = "CWE-294"
IOTBENCH_VULN_INSTALL = "cwe294-mqtt-replay"
