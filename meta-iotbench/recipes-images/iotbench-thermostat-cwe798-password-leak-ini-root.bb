require recipes-images/iotbench-image.inc
require recipes-devices/thermostat/device-thermostat.inc
IOTBENCH_PASSWORD_LEAK_VARIANT = "ini-root"
require recipes-images/iotbench-password-leak.inc

SUMMARY = "IoTBench fixture - thermostat, CWE-798 password leak ini-root"
