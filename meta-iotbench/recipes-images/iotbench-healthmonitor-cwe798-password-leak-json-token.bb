require recipes-images/iotbench-image.inc
require recipes-devices/healthmonitor/device-healthmonitor.inc
IOTBENCH_PASSWORD_LEAK_VARIANT = "json-token"
require recipes-images/iotbench-password-leak.inc

SUMMARY = "IoTBench fixture - healthmonitor, CWE-798 password leak json-token"
