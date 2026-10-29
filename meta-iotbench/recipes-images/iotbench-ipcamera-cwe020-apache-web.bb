require recipes-images/iotbench-image.inc
require recipes-devices/ipcamera/device-ipcamera.inc

SUMMARY = "IoTBench synthetic ipcamera, Apache application CWE-020"
APACHE_FIXTURE_CWE = "020"
require recipes-images/iotbench-apache-fixture.inc
