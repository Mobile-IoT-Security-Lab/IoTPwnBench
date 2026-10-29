require recipes-images/iotbench-image.inc
require recipes-devices/smartbulb/device-smartbulb.inc
IOTBENCH_PASSWORD_LEAK_VARIANT = "env-base64"
require recipes-images/iotbench-password-leak.inc

SUMMARY = "IoTBench fixture - smartbulb, CWE-798 password leak env-base64"
