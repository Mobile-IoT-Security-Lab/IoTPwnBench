require recipes-images/iotbench-image.inc
require recipes-devices/smartplug/device-smartplug.inc

SUMMARY = "IoTBench target - smart plug, CWE-862 missing authorization"
DESCRIPTION = "Smart plug firmware whose MQTT relay command accepts an actor that is not authorized for the target device."

IOTBENCH_CWE = "CWE-862"
IOTBENCH_VULN_INSTALL = "cwe862-smartplug-missing-authorization"
