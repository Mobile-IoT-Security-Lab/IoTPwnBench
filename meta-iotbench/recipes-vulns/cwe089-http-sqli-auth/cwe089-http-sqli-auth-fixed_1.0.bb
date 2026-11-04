require recipes-vulns/cwe089-http-sqli-auth/cwe089-http-sqli-auth_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-89 HTTP login SQL injection"
DESCRIPTION = "Corrected twin of cwe089-http-sqli-auth. User input is quoted as an SQL string literal. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
