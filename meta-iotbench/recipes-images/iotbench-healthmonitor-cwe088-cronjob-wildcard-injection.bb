# INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE - NOT FOR DEPLOYMENT
require recipes-images/iotbench-image.inc
require recipes-devices/healthmonitor/device-healthmonitor.inc
require recipes-images/iotbench-cronjob-wildcard-injection.inc

SUMMARY = "IoTBench target - healthmonitor, cron wildcard argument injection (CWE-88)"
DESCRIPTION = "One diagnostic-only wildcard injection scenario; explicit test builds only."
