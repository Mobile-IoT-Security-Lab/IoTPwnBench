require recipes-images/iotbench-image.inc
require recipes-devices/thermostat/device-thermostat.inc
require recipes-images/iotbench-hardcoded-user-passwords.inc

SUMMARY = "IoTBench fixture - thermostat, CWE-798 hardcoding user passwords"
DESCRIPTION = "INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT. Fixed synthetic local application account password embedded in firmware."
IOTBENCH_CWE = "CWE-798"
IOTBENCH_VULN_INSTALL = "cwe798-hardcoded-user-passwords"
