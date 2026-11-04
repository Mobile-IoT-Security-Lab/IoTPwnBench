require recipes-vulns/cwe798-hardcoded-credentials/cwe798-hardcoded-credentials_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-798 hardcoded credentials"
DESCRIPTION = "Corrected twin of cwe798-hardcoded-credentials. No credential is shipped, support access needs a per-device enrolled password hash. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
