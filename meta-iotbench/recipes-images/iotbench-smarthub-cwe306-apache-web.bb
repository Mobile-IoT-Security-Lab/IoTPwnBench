require recipes-images/iotbench-image.inc
require recipes-devices/smarthub/device-smarthub.inc

SUMMARY = "IoTBench synthetic smarthub, Apache application CWE-306"
APACHE_FIXTURE_CWE = "306"
require recipes-images/iotbench-apache-fixture.inc
