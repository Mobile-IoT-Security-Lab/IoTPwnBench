require recipes-images/iotbench-image.inc
require recipes-devices/envsensor/device-envsensor.inc
IOTBENCH_PASSWORD_LEAK_VARIANT = "conf-password"
require recipes-images/iotbench-password-leak.inc

SUMMARY = "IoTBench fixture - envsensor, CWE-798 password leak conf-password"
