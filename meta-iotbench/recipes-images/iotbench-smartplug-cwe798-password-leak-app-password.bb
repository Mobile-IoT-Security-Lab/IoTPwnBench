require recipes-images/iotbench-image.inc
require recipes-devices/smartplug/device-smartplug.inc
IOTBENCH_PASSWORD_LEAK_VARIANT = "app-password"
require recipes-images/iotbench-password-leak.inc

SUMMARY = "IoTBench fixture - smartplug, CWE-798 password leak app-password"
