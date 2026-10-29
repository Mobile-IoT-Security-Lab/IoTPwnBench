require recipes-images/iotbench-image.inc
require recipes-devices/envsensor/device-envsensor.inc

SUMMARY = "IoTBench synthetic envsensor, Apache application CWE-077"
APACHE_FIXTURE_CWE = "077"
require recipes-images/iotbench-apache-fixture.inc
