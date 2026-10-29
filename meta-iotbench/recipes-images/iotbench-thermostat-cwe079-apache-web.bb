require recipes-images/iotbench-image.inc
require recipes-devices/thermostat/device-thermostat.inc

SUMMARY = "IoTBench synthetic thermostat, Apache application CWE-079"
APACHE_FIXTURE_CWE = "079"
require recipes-images/iotbench-apache-fixture.inc
