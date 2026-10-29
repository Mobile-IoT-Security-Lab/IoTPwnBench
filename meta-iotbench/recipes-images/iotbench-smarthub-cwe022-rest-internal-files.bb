# INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE - NOT FOR DEPLOYMENT
require recipes-images/iotbench-image.inc
require recipes-devices/smarthub/device-smarthub.inc
require recipes-images/iotbench-rest-internal-files.inc

SUMMARY = "IoTBench target - smarthub, REST internal file traversal (CWE-22/CWE-73)"
DESCRIPTION = "One read-only synthetic REST path traversal; explicit test builds only."
