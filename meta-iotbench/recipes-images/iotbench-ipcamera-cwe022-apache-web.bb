require recipes-images/iotbench-image.inc
require recipes-devices/ipcamera/device-ipcamera.inc

SUMMARY = "IoTBench synthetic ipcamera, Apache application CWE-022"
APACHE_FIXTURE_CWE = "022"
require recipes-images/iotbench-apache-fixture.inc
