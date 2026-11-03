# INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE - NOT FOR DEPLOYMENT
require recipes-images/iotbench-image.inc
require recipes-devices/doorlock/device-doorlock.inc
require recipes-images/iotbench-rest-internal-files.inc

SUMMARY = "IoTBench corrected twin - doorlock, REST internal file traversal (CWE-22/CWE-73)"
DESCRIPTION = "Corrected twin of iotbench-doorlock-cwe022-rest-internal-files. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
