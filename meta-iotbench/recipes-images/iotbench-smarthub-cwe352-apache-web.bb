require recipes-images/iotbench-image.inc
require recipes-devices/smarthub/device-smarthub.inc

SUMMARY = "IoTBench synthetic smarthub, Apache application CWE-352"
APACHE_FIXTURE_CWE = "352"
require recipes-images/iotbench-apache-fixture.inc
