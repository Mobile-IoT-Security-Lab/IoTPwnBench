require recipes-images/iotbench-image.inc
require recipes-devices/healthmonitor/device-healthmonitor.inc

SUMMARY = "IoTBench synthetic healthmonitor, Apache application CWE-089"
APACHE_FIXTURE_CWE = "089"
require recipes-images/iotbench-apache-fixture.inc
