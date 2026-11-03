require recipes-vulns/cwe089-c-sql-injection/cwe089-c-sql-injection_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-89 C SQL injection"
DESCRIPTION = "Corrected twin of cwe089-c-sql-injection. The input is bound as a SQL value. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
