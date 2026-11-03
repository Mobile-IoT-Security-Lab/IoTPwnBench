require recipes-vulns/cwe798-embedded-auth/cwe798-embedded-auth-json_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-798 embedded authentication, json"
DESCRIPTION = "Corrected twin of the embedded authentication fixture. The artifact names the secret slot only, the password is provisioned at runtime. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
