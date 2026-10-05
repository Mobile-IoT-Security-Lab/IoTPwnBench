require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench target - router, CWE-78 root cron command injection"
DESCRIPTION = "Router firmware whose root maintenance job interpolates a web-user-controlled target into a shell command."

IOTBENCH_CWE = "CWE-78"
IOTBENCH_VULN_INSTALL = "cwe078-writable-root-cron"
