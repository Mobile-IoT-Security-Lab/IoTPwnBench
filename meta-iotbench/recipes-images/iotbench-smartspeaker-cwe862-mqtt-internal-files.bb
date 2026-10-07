require recipes-images/iotbench-image.inc
require recipes-devices/smartspeaker/device-smartspeaker.inc
require recipes-images/iotbench-mqtt-internal-files.inc

SUMMARY = "IoTBench fixture - smartspeaker, CWE-862 MQTT internal-file exposure"
DESCRIPTION = "INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT. A local MQTT broker exposes predefined internal synthetic files through insufficiently restricted topics."
IOTBENCH_CWE = "CWE-862"
IOTBENCH_VULN_INSTALL = "cwe862-mqtt-internal-files"
