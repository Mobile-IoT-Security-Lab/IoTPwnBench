# INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE - NOT FOR DEPLOYMENT
require recipes-images/iotbench-image.inc
require recipes-devices/ipcamera/device-ipcamera.inc
PATH_FIXTURE_CWE = "020"
PATH_FIXTURE_PACKAGE = "cwe020-native-filename-validation"
require recipes-images/iotbench-native-path-fixture.inc

SUMMARY = "IoTBench corrected twin - ipcamera, native native-filename-validation (CWE-20)"
DESCRIPTION = "Corrected twin of iotbench-ipcamera-cwe020-native-filename-validation. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
