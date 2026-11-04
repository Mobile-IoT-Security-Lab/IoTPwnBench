require recipes-vulns/cwe798-vi-privilege-escalation/cwe798-vi-privilege-escalation_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-798 vi privilege escalation"
DESCRIPTION = "Corrected twin of cwe798-vi-privilege-escalation. The sudo rule allows one fixed command and not an editor. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
