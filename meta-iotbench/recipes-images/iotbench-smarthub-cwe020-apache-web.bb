require recipes-images/iotbench-image.inc
require recipes-devices/smarthub/device-smarthub.inc

SUMMARY = "IoTBench synthetic smarthub, Apache application CWE-020"
APACHE_FIXTURE_CWE = "020"
require recipes-images/iotbench-apache-fixture.inc
