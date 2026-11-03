require recipes-vulns/cwe078-os-command-injection/cwe078-os-command-injection_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-78 OS command injection"
DESCRIPTION = "Corrected twin of cwe078-os-command-injection. The target is validated and ping is started without a shell. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
