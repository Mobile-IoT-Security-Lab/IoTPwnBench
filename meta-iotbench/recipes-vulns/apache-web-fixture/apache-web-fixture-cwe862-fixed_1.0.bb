require recipes-vulns/apache-web-fixture/apache-web-fixture-cwe862_1.0.bb

SUMMARY = "IoTBench corrected variant - Apache application, CWE-862"
DESCRIPTION = "Corrected twin of the Apache application fixture. The defect of the matching variant is removed. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
