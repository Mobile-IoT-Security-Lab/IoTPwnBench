require recipes-images/iotbench-image.inc
require recipes-devices/envsensor/device-envsensor.inc

SUMMARY = "IoTBench corrected twin - environmental sensor, CWE-306 unauthenticated calibration"
DESCRIPTION = "Corrected twin of iotbench-envsensor-cwe306-unauthenticated-calibration. The same device and service, with the weakness removed. No weakness is injected."

IOTBENCH_CWE = "CWE-306"
IOTBENCH_VULN_INSTALL = "cwe306-envsensor-unauth-calibration-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
