require recipes-vulns/cwe400-diagnostic-dos/cwe400-diagnostic-dos_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-400 diagnostic denial of service"
DESCRIPTION = "Corrected twin of cwe400-diagnostic-dos. The requested allocation is limited to 16 MB. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
