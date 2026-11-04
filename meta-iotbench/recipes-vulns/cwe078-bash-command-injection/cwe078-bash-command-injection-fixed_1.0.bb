require recipes-vulns/cwe078-bash-command-injection/cwe078-bash-command-injection_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-78 Bash command injection"
DESCRIPTION = "Corrected twin of cwe078-bash-command-injection. The target is printed as data and never evaluated. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
