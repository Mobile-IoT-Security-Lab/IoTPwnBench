require recipes-vulns/cwe078-mqtt-command-injection/cwe078-mqtt-command-injection_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-78 MQTT command injection"
DESCRIPTION = "Corrected twin of cwe078-mqtt-command-injection. The MQTT value is validated and never reaches a shell. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
