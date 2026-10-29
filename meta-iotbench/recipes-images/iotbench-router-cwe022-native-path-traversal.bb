# INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE - NOT FOR DEPLOYMENT
require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc
PATH_FIXTURE_CWE = "022"
PATH_FIXTURE_PACKAGE = "cwe022-native-path-traversal"
require recipes-images/iotbench-native-path-fixture.inc

SUMMARY = "IoTBench target - router, native native-path-traversal (CWE-22)"
