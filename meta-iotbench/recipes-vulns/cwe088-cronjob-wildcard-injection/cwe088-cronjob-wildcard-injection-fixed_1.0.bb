require recipes-vulns/cwe088-cronjob-wildcard-injection/cwe088-cronjob-wildcard-injection_1.0.bb

SUMMARY = "IoTBench corrected variant - cron wildcard injection, CWE-88"
DESCRIPTION = "Corrected twin of the cron wildcard fixture. The scheduled command separates operands from options with --. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
