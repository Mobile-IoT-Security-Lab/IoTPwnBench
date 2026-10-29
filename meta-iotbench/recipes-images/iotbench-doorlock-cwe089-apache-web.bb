require recipes-images/iotbench-image.inc
require recipes-devices/doorlock/device-doorlock.inc

SUMMARY = "IoTBench synthetic doorlock, Apache application CWE-089"
APACHE_FIXTURE_CWE = "089"
require recipes-images/iotbench-apache-fixture.inc
