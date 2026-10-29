require recipes-images/iotbench-image.inc
require recipes-devices/smartspeaker/device-smartspeaker.inc
IOTBENCH_PASSWORD_LEAK_VARIANT = "c-password"
require recipes-images/iotbench-password-leak.inc

SUMMARY = "IoTBench fixture - smartspeaker, CWE-798 password leak c-password"
