require recipes-vulns/cwe276-bad-chown-rights/cwe276-bad-chown-rights_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-276 bad chown rights"
DESCRIPTION = "Corrected twin of cwe276-bad-chown-rights. The root-consumed WAN policy file is owned by root and is not writable by the web user. No weakness is injected."

do_install() {
    install -d ${D}${sysconfdir}/iotbench
    install -m 0644 ${S}/wan-policy.conf ${D}${sysconfdir}/iotbench/wan-policy.conf
    chown 0:0 ${D}${sysconfdir}/iotbench/wan-policy.conf
}
