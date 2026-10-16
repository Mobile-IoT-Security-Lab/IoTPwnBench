# INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT
require recipes-images/iotbench-image.inc
require recipes-devices/plc/device-plc.inc
require recipes-images/iotbench-service-buffer-overflow.inc

SUMMARY = "IoTBench target - plc, CWE-120 buffer overflow via local service"
DESCRIPTION = "INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT"
IOTBENCH_CWE = "CWE-120"
IOTBENCH_VULN_INSTALL = "cwe120-service-buffer-overflow"
