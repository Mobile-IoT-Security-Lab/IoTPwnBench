require recipes-images/iotbench-image.inc
require recipes-devices/plc/device-plc.inc
IOTBENCH_PASSWORD_LEAK_VARIANT = "init-password"
require recipes-images/iotbench-password-leak.inc

SUMMARY = "IoTBench fixture - plc, CWE-798 password leak init-password"
