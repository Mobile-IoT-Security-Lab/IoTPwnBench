require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench synthetic router, Apache application CWE-020"
APACHE_FIXTURE_CWE = "020"
require recipes-images/iotbench-apache-fixture.inc
