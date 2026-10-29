# INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE - NOT FOR DEPLOYMENT
require recipes-images/iotbench-image.inc
require recipes-devices/smartbulb/device-smartbulb.inc
PATH_FIXTURE_CWE = "020"
PATH_FIXTURE_PACKAGE = "cwe020-native-filename-validation"
require recipes-images/iotbench-native-path-fixture.inc

SUMMARY = "IoTBench target - smartbulb, native native-filename-validation (CWE-20)"
