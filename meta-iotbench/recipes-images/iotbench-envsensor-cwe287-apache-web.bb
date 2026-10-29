require recipes-images/iotbench-image.inc
require recipes-devices/envsensor/device-envsensor.inc

SUMMARY = "IoTBench synthetic envsensor, Apache application CWE-287"
APACHE_FIXTURE_CWE = "287"
require recipes-images/iotbench-apache-fixture.inc
