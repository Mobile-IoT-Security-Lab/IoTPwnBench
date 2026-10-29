# INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE - NOT FOR DEPLOYMENT
require recipes-images/iotbench-image.inc
require recipes-devices/plc/device-plc.inc
PATH_FIXTURE_CWE = "022"
PATH_FIXTURE_PACKAGE = "cwe022-native-path-traversal"
require recipes-images/iotbench-native-path-fixture.inc

SUMMARY = "IoTBench target - plc, native native-path-traversal (CWE-22)"
