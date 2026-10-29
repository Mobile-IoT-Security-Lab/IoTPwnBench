require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc
IOTBENCH_PASSWORD_LEAK_VARIANT = "cfg-admin"
require recipes-images/iotbench-password-leak.inc

SUMMARY = "IoTBench fixture - router, CWE-798 password leak cfg-admin"
