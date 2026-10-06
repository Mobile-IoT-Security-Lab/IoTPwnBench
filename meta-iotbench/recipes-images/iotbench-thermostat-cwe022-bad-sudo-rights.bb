require recipes-images/iotbench-image.inc
require recipes-images/iotbench-bad-sudo-rights.inc
require recipes-devices/thermostat/device-thermostat.inc

SUMMARY = "IoTBench target - thermostat, CWE-22 bad sudo rights path traversal"
IOTBENCH_CWE = "CWE-22"
IOTBENCH_VULN_INSTALL = "cwe022-bad-sudo-rights"
