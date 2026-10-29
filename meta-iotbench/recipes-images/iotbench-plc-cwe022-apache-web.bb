require recipes-images/iotbench-image.inc
require recipes-devices/plc/device-plc.inc

SUMMARY = "IoTBench synthetic plc, Apache application CWE-022"
APACHE_FIXTURE_CWE = "022"
require recipes-images/iotbench-apache-fixture.inc
