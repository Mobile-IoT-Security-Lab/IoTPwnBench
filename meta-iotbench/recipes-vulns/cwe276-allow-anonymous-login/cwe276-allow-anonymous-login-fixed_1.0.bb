require recipes-vulns/cwe276-allow-anonymous-login/cwe276-allow-anonymous-login_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-276 allow anonymous login"
DESCRIPTION = "Corrected twin of cwe276-allow-anonymous-login. Anonymous FTP is disabled. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
