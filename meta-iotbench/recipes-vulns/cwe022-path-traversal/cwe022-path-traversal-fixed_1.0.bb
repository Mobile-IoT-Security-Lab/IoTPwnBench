require recipes-vulns/cwe022-path-traversal/cwe022-path-traversal_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-22 path traversal"
DESCRIPTION = "Corrected twin of cwe022-path-traversal. The path is decoded once and confined to the reports directory. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
