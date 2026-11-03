require recipes-vulns/cwe276-permit-root-login/cwe276-permit-root-login_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-276 permit root login"
DESCRIPTION = "Corrected twin of cwe276-permit-root-login. The SSH daemon refuses root logins. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
