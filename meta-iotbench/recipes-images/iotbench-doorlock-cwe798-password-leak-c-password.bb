require recipes-images/iotbench-image.inc
require recipes-devices/doorlock/device-doorlock.inc
IOTBENCH_PASSWORD_LEAK_VARIANT = "c-password"
require recipes-images/iotbench-password-leak.inc

SUMMARY = "IoTBench fixture - doorlock, CWE-798 password leak c-password"
