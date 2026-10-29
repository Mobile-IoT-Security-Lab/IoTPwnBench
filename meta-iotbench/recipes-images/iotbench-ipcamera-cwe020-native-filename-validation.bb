# INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE - NOT FOR DEPLOYMENT
require recipes-images/iotbench-image.inc
require recipes-devices/ipcamera/device-ipcamera.inc
PATH_FIXTURE_CWE = "020"
PATH_FIXTURE_PACKAGE = "cwe020-native-filename-validation"
require recipes-images/iotbench-native-path-fixture.inc

SUMMARY = "IoTBench target - ipcamera, native native-filename-validation (CWE-20)"
