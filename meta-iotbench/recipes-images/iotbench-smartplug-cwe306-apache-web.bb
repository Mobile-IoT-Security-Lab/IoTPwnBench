require recipes-images/iotbench-image.inc
require recipes-devices/smartplug/device-smartplug.inc

SUMMARY = "IoTBench synthetic smartplug, Apache application CWE-306"
APACHE_FIXTURE_CWE = "306"
require recipes-images/iotbench-apache-fixture.inc
