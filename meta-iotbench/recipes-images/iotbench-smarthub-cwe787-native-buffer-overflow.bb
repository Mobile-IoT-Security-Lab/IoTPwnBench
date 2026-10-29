require recipes-images/iotbench-image.inc
require recipes-devices/smarthub/device-smarthub.inc
require recipes-images/iotbench-native-buffer-overflow.inc

SUMMARY = "IoTBench fixture - smarthub, CWE-787 native C buffer overflow"
DESCRIPTION = "INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE - LOCAL SECURITY TESTING ONLY - NOT FOR DEPLOYMENT. One unchecked indexed write; CWE-20 contributes, CWE-119 is the broader category."
IOTBENCH_CWE = "CWE-787"
IOTBENCH_VULN_INSTALL = "cwe787-native-buffer-overflow"
