# INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE - NOT FOR DEPLOYMENT
require recipes-images/iotbench-image.inc
require recipes-devices/ipcamera/device-ipcamera.inc
require recipes-images/iotbench-cronjob-wildcard-injection.inc

SUMMARY = "IoTBench target - ipcamera, cron wildcard argument injection (CWE-88)"
DESCRIPTION = "One diagnostic-only wildcard injection scenario; explicit test builds only."
