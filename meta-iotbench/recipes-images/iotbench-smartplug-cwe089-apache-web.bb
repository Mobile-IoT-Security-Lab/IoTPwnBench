require recipes-images/iotbench-image.inc
require recipes-devices/smartplug/device-smartplug.inc

SUMMARY = "IoTBench synthetic smartplug, Apache application CWE-089"
APACHE_FIXTURE_CWE = "089"
require recipes-images/iotbench-apache-fixture.inc
