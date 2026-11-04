require recipes-vulns/cwe078-ipcamera-ptz-command-injection/cwe078-ipcamera-ptz-command-injection_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-78 IP camera PTZ command injection"
DESCRIPTION = "Corrected twin of cwe078-ipcamera-ptz-command-injection. The preset name is restricted to a safe character set. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
