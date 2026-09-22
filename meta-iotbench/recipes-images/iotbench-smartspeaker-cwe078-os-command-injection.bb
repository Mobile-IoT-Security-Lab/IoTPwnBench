require recipes-images/iotbench-image.inc
require recipes-devices/smartspeaker/device-smartspeaker.inc

SUMMARY = "IoTBench target - smartspeaker, CWE-78 OS command injection (ping diagnostic)"
DESCRIPTION = "smartspeaker firmware whose web-admin ping diagnostic passes unsanitized input to a shell command, exposing OS command injection (CWE-78)."

IOTBENCH_CWE = "CWE-78"
IOTBENCH_VULN_INSTALL = "cwe078-os-command-injection"
