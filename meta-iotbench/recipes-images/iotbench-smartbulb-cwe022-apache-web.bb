require recipes-images/iotbench-image.inc
require recipes-devices/smartbulb/device-smartbulb.inc

SUMMARY = "IoTBench synthetic smartbulb, Apache application CWE-022"
APACHE_FIXTURE_CWE = "022"
require recipes-images/iotbench-apache-fixture.inc
