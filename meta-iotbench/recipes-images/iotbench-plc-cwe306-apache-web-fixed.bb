require recipes-images/iotbench-image.inc
require recipes-devices/plc/device-plc.inc

SUMMARY = "IoTBench corrected twin - plc-cwe306-apache-web"
APACHE_FIXTURE_CWE = "306"
require recipes-images/iotbench-apache-fixture.inc
DESCRIPTION = "Corrected twin of iotbench-plc-cwe306-apache-web. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
