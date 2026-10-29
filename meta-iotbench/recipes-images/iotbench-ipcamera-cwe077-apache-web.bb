require recipes-images/iotbench-image.inc
require recipes-devices/ipcamera/device-ipcamera.inc

SUMMARY = "IoTBench synthetic ipcamera, Apache application CWE-077"
APACHE_FIXTURE_CWE = "077"
require recipes-images/iotbench-apache-fixture.inc
