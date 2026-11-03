# INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT
require recipes-images/iotbench-image.inc
require recipes-devices/envsensor/device-envsensor.inc
require recipes-images/iotbench-service-buffer-overflow.inc

SUMMARY = "IoTBench corrected twin - envsensor, CWE-120 buffer overflow via local service"
DESCRIPTION = "Corrected twin of iotbench-envsensor-cwe120-service-buffer-overflow. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_CWE = "CWE-120"
IOTBENCH_VULN_INSTALL = "cwe120-service-buffer-overflow-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
