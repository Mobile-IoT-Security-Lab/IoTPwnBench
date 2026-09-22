require recipes-images/iotbench-image.inc
require recipes-devices/healthmonitor/device-healthmonitor.inc

SUMMARY = "IoTBench target - healthmonitor, CWE-78 OS command injection (ping diagnostic)"
DESCRIPTION = "healthmonitor firmware whose web-admin ping diagnostic passes unsanitized input to a shell command, exposing OS command injection (CWE-78)."

IOTBENCH_CWE = "CWE-78"
IOTBENCH_VULN_INSTALL = "cwe078-os-command-injection"
