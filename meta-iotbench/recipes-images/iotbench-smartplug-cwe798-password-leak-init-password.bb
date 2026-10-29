require recipes-images/iotbench-image.inc
require recipes-devices/smartplug/device-smartplug.inc
IOTBENCH_PASSWORD_LEAK_VARIANT = "init-password"
require recipes-images/iotbench-password-leak.inc

SUMMARY = "IoTBench fixture - smartplug, CWE-798 password leak init-password"
