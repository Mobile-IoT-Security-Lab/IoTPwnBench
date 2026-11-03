# INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE - NOT FOR DEPLOYMENT
require recipes-images/iotbench-image.inc
require recipes-devices/thermostat/device-thermostat.inc
PATH_FIXTURE_CWE = "022"
PATH_FIXTURE_PACKAGE = "cwe022-native-path-traversal"
require recipes-images/iotbench-native-path-fixture.inc

SUMMARY = "IoTBench corrected twin - thermostat, native native-path-traversal (CWE-22)"
DESCRIPTION = "Corrected twin of iotbench-thermostat-cwe022-native-path-traversal. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
