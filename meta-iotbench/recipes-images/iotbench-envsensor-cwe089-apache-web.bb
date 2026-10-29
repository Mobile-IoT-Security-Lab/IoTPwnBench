require recipes-images/iotbench-image.inc
require recipes-devices/envsensor/device-envsensor.inc

SUMMARY = "IoTBench synthetic envsensor, Apache application CWE-089"
APACHE_FIXTURE_CWE = "089"
require recipes-images/iotbench-apache-fixture.inc
