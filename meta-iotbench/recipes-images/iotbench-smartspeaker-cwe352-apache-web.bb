require recipes-images/iotbench-image.inc
require recipes-devices/smartspeaker/device-smartspeaker.inc

SUMMARY = "IoTBench synthetic smartspeaker, Apache application CWE-352"
APACHE_FIXTURE_CWE = "352"
require recipes-images/iotbench-apache-fixture.inc
