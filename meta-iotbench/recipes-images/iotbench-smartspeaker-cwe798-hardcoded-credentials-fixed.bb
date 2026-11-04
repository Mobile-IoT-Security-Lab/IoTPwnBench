require recipes-images/iotbench-image.inc
require recipes-devices/smartspeaker/device-smartspeaker.inc

SUMMARY = "IoTBench corrected twin - smartspeaker, CWE-798 hardcoded credentials"
DESCRIPTION = "Corrected twin of iotbench-smartspeaker-cwe798-hardcoded-credentials. The same device and service, with the weakness removed. No weakness is injected."

IOTBENCH_CWE = "CWE-798"
IOTBENCH_VULN_INSTALL = "cwe798-hardcoded-credentials-fixed"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
