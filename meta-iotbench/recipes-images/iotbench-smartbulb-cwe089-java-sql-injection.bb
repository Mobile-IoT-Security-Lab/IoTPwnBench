require recipes-images/iotbench-image.inc
require recipes-devices/smartbulb/device-smartbulb.inc
require recipes-images/iotbench-java-sql-injection.inc

SUMMARY = "IoTBench fixture - smartbulb, CWE-89 Java JAR SQL injection"
DESCRIPTION = "INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT. Java bytecode concatenates local input into a read-only SQLite JDBC SELECT."
IOTBENCH_CWE = "CWE-89"
IOTBENCH_VULN_INSTALL = "cwe089-java-sql-injection"
