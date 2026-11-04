require recipes-vulns/cwe078-writable-root-cron/cwe078-writable-root-cron_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-78 writable root cron target"
DESCRIPTION = "Corrected twin of cwe078-writable-root-cron. The target is printed as data and never evaluated. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
