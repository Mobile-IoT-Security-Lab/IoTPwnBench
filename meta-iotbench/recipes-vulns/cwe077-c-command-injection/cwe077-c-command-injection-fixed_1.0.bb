require recipes-vulns/cwe077-c-command-injection/cwe077-c-command-injection_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-77 C command injection"
DESCRIPTION = "Corrected twin of cwe077-c-command-injection. The target is printed as data and no shell is started. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
