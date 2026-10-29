require recipes-images/iotbench-image.inc
require recipes-devices/healthmonitor/device-healthmonitor.inc

SUMMARY = "IoTBench synthetic healthmonitor, Apache application CWE-020"
APACHE_FIXTURE_CWE = "020"
require recipes-images/iotbench-apache-fixture.inc
