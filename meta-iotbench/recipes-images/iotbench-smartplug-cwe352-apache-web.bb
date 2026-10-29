require recipes-images/iotbench-image.inc
require recipes-devices/smartplug/device-smartplug.inc

SUMMARY = "IoTBench synthetic smartplug, Apache application CWE-352"
APACHE_FIXTURE_CWE = "352"
require recipes-images/iotbench-apache-fixture.inc
