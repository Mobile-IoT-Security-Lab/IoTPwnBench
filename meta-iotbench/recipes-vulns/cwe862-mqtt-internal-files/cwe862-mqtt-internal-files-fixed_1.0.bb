require recipes-vulns/cwe862-mqtt-internal-files/cwe862-mqtt-internal-files_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-862 MQTT internal files"
DESCRIPTION = "Corrected twin of cwe862-mqtt-internal-files. The public ACL does not grant read access to the internal topics. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
