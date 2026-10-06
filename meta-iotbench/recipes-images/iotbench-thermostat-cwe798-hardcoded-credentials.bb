require recipes-images/iotbench-image.inc
require recipes-devices/thermostat/device-thermostat.inc

SUMMARY = "IoTBench target - thermostat, CWE-798 hardcoded credentials"
DESCRIPTION = "thermostat firmware with vendor support backup access using shared credentials embedded in the firmware."

IOTBENCH_CWE = "CWE-798"
IOTBENCH_VULN_INSTALL = "cwe798-hardcoded-credentials"
