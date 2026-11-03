require recipes-vulns/cwe121-plc-modbus-stack-overflow/cwe121-plc-modbus-stack-overflow_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-121 PLC Modbus stack overflow"
DESCRIPTION = "Corrected twin of cwe121-plc-modbus-stack-overflow. The project chunk length is checked against the 32-byte field. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
