require recipes-vulns/cwe862-smartplug-missing-authorization/cwe862-smartplug-missing-authorization_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-862 smart plug missing authorization"
DESCRIPTION = "Corrected twin of cwe862-smartplug-missing-authorization. The actor must be the owner before the relay changes. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
