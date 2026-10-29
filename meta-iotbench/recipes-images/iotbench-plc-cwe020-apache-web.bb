require recipes-images/iotbench-image.inc
require recipes-devices/plc/device-plc.inc

SUMMARY = "IoTBench synthetic plc, Apache application CWE-020"
APACHE_FIXTURE_CWE = "020"
require recipes-images/iotbench-apache-fixture.inc
