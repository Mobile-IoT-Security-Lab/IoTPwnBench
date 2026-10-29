# INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE - NOT FOR DEPLOYMENT
require recipes-images/iotbench-image.inc
require recipes-devices/smarthub/device-smarthub.inc
require recipes-images/iotbench-cronjob-wildcard-injection.inc

SUMMARY = "IoTBench target - smarthub, cron wildcard argument injection (CWE-88)"
DESCRIPTION = "One diagnostic-only wildcard injection scenario; explicit test builds only."
