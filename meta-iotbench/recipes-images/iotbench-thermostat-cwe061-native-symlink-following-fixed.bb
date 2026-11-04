# INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE - NOT FOR DEPLOYMENT
require recipes-images/iotbench-image.inc
require recipes-devices/thermostat/device-thermostat.inc
require recipes-images/iotbench-native-symlink-fixture.inc

SUMMARY = "IoTBench corrected twin - thermostat, native symlink following (CWE-61)"
DESCRIPTION = "Corrected twin of iotbench-thermostat-cwe061-native-symlink-following. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
