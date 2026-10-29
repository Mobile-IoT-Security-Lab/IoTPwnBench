require recipes-images/iotbench-image.inc
require recipes-devices/thermostat/device-thermostat.inc
require recipes-images/iotbench-native-connection-string.inc

SUMMARY = "IoTBench fixture - thermostat, CWE-20 native C connection string injection"
DESCRIPTION = "INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE - LOCAL SECURITY TESTING ONLY - NOT FOR DEPLOYMENT. One missing cache-value validation allows a SQLite URI parameter change."
IOTBENCH_CWE = "CWE-20"
IOTBENCH_VULN_INSTALL = "cwe020-native-connection-string"
