require recipes-images/iotbench-image.inc
require recipes-devices/envsensor/device-envsensor.inc
require recipes-images/iotbench-c-sql-injection.inc

SUMMARY = "IoTBench fixture - envsensor, CWE-89 native C SQL injection"
DESCRIPTION = "INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT. Local native C lookup interpolates input into a read-only synthetic SQLite SELECT."
IOTBENCH_CWE = "CWE-89"
IOTBENCH_VULN_INSTALL = "cwe089-c-sql-injection"
