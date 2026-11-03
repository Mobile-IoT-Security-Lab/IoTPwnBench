require recipes-vulns/native-path-fixture/cwe022-native-path-traversal_1.0.bb

SUMMARY = "IoTBench corrected variant - native path fixture, CWE-22"
DESCRIPTION = "Corrected twin of the native path fixture. The flaw is removed from the request handling. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
