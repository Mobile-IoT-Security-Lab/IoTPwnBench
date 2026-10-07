require recipes-images/iotbench-image.inc
require recipes-devices/smartspeaker/device-smartspeaker.inc
require recipes-images/iotbench-coap-internal-files.inc

SUMMARY = "IoTBench fixture - smartspeaker, CWE-862 CoAP internal-file exposure"
DESCRIPTION = "INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT. CoAP resources expose predefined internal synthetic files without authorization."
IOTBENCH_CWE = "CWE-862"
IOTBENCH_VULN_INSTALL = "cwe862-coap-internal-files"
