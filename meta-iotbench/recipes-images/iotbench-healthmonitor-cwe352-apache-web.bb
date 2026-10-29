require recipes-images/iotbench-image.inc
require recipes-devices/healthmonitor/device-healthmonitor.inc

SUMMARY = "IoTBench synthetic healthmonitor, Apache application CWE-352"
APACHE_FIXTURE_CWE = "352"
require recipes-images/iotbench-apache-fixture.inc
