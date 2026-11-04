require recipes-vulns/cwe089-java-sql-injection/cwe089-java-sql-injection_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-89 Java SQL injection"
DESCRIPTION = "Corrected twin of cwe089-java-sql-injection. The input is bound as a SQL value. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
