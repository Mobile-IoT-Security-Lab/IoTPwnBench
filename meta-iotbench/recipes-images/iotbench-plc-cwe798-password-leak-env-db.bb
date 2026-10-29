require recipes-images/iotbench-image.inc
require recipes-devices/plc/device-plc.inc
IOTBENCH_PASSWORD_LEAK_VARIANT = "env-db"
require recipes-images/iotbench-password-leak.inc

SUMMARY = "IoTBench fixture - plc, CWE-798 password leak env-db"
