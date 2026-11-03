require recipes-vulns/cwe798-sudo-environment/cwe798-sudo-environment_1.0.bb

SUMMARY = "IoTBench corrected variant - sudo environment, CWE-798"
DESCRIPTION = "Corrected twin of the sudo environment fixture. The environment is reset and the diagnostic credential is removed. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
