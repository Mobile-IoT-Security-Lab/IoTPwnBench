require recipes-vulns/cwe798-password-leak/cwe798-password-leak-env-db_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-798 password leak, env-db"
DESCRIPTION = "Corrected twin of the password leak fixture. The credential is no longer stored in the file, it is provisioned at runtime. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
