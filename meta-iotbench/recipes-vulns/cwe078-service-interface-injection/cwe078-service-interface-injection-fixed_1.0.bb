require recipes-vulns/cwe078-service-interface-injection/cwe078-service-interface-injection_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-78 service interface injection"
DESCRIPTION = "Corrected twin of cwe078-service-interface-injection. The service name is validated and no shell is started. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
