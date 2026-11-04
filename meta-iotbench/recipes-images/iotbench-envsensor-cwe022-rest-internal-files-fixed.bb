# INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE - NOT FOR DEPLOYMENT
require recipes-images/iotbench-image.inc
require recipes-devices/envsensor/device-envsensor.inc
require recipes-images/iotbench-rest-internal-files.inc

SUMMARY = "IoTBench corrected twin - envsensor, REST internal file traversal (CWE-22/CWE-73)"
DESCRIPTION = "Corrected twin of iotbench-envsensor-cwe022-rest-internal-files. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
