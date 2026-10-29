require recipes-images/iotbench-image.inc
require recipes-devices/envsensor/device-envsensor.inc
IOTBENCH_PASSWORD_LEAK_VARIANT = "log-password"
require recipes-images/iotbench-password-leak.inc

SUMMARY = "IoTBench fixture - envsensor, CWE-798 password leak log-password"
