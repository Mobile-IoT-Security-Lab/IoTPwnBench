require recipes-images/iotbench-image.inc
require recipes-devices/plc/device-plc.inc

SUMMARY = "IoTBench synthetic plc, Apache application CWE-078"
APACHE_FIXTURE_CWE = "078"
require recipes-images/iotbench-apache-fixture.inc
