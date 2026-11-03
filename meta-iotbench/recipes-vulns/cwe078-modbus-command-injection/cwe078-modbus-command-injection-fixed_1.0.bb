require recipes-vulns/cwe078-modbus-command-injection/cwe078-modbus-command-injection_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-78 Modbus command injection"
DESCRIPTION = "Corrected twin of cwe078-modbus-command-injection. The project name is validated and no shell is started. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
