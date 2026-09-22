require recipes-images/iotbench-image.inc
require recipes-devices/plc/device-plc.inc

SUMMARY = "IoTBench target - plc, CWE-78 OS command injection (ping diagnostic)"
DESCRIPTION = "plc firmware whose web-admin ping diagnostic passes unsanitized input to a shell command, exposing OS command injection (CWE-78)."

IOTBENCH_CWE = "CWE-78"
IOTBENCH_VULN_INSTALL = "cwe078-os-command-injection"
