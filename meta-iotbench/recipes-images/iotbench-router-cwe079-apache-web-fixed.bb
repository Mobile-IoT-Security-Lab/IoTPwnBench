require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench corrected twin - router-cwe079-apache-web"
APACHE_FIXTURE_CWE = "079"
require recipes-images/iotbench-apache-fixture.inc
DESCRIPTION = "Corrected twin of iotbench-router-cwe079-apache-web. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_TWIN = "1"
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
