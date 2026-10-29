require recipes-images/iotbench-image.inc
require recipes-devices/envsensor/device-envsensor.inc
IOTBENCH_PASSWORD_LEAK_VARIANT = "json-token"
require recipes-images/iotbench-password-leak.inc

SUMMARY = "IoTBench fixture - envsensor, CWE-798 password leak json-token"
