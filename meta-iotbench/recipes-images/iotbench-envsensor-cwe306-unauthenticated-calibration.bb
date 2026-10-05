require recipes-images/iotbench-image.inc
require recipes-devices/envsensor/device-envsensor.inc

SUMMARY = "IoTBench target - environmental sensor, CWE-306 unauthenticated calibration"
DESCRIPTION = "Environmental sensor firmware that accepts critical calibration changes without authentication."

IOTBENCH_CWE = "CWE-306"
IOTBENCH_VULN_INSTALL = "cwe306-envsensor-unauth-calibration"
