require recipes-vulns/cwe022-ipcamera-recording-traversal/cwe022-ipcamera-recording-traversal_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-22 IP camera recording traversal"
DESCRIPTION = "Corrected twin of cwe022-ipcamera-recording-traversal. Only plain recording file names are accepted. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
