require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench target - router, CWE-78 writable root cron script"
DESCRIPTION = "Router firmware with a root cron entry invoking a web-user-writable script."

IOTBENCH_CWE = "CWE-78"
IOTBENCH_VULN_INSTALL = "cwe078-writable-root-cron"
