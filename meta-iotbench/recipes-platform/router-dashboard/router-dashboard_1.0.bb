SUMMARY = "Embedded router management dashboard (IoTBench platform)"
DESCRIPTION = "Responsive PHP dashboard showing live target metrics and safely \
simulated router settings. Vulnerability modules plug into it through the \
modules directory; this core recipe ships no vulnerability."
HOMEPAGE = "https://example.invalid/router-dashboard"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"

SRC_URI = "file://LICENSE \
           file://index.php \
           file://api.php \
           file://router.php \
           file://app.css \
           file://app.js \
           file://settings.json"

S = "${UNPACKDIR}"

inherit useradd

USERADD_PACKAGES = "${PN}"
USERADD_PARAM:${PN} = "--system --uid 995 --home-dir ${localstatedir}/lib/router-dashboard --no-create-home --shell /sbin/nologin --user-group routerweb"

RDEPENDS:${PN} = "lighttpd lighttpd-module-cgi php-cgi"

do_install() {
    install -d ${D}/www/pages/assets
    install -m 0644 ${S}/index.php ${D}/www/pages/index.php
    install -m 0644 ${S}/api.php ${D}/www/pages/api.php
    install -m 0644 ${S}/app.css ${D}/www/pages/assets/app.css
    install -m 0644 ${S}/app.js ${D}/www/pages/assets/app.js

    install -d ${D}${datadir}/router-dashboard
    install -m 0644 ${S}/router.php ${D}${datadir}/router-dashboard/router.php
    # Vulnerability modules drop a <id>/module.php into this directory.
    install -d ${D}${datadir}/router-dashboard/modules

    install -d -m 0750 ${D}${localstatedir}/lib/router-dashboard
    install -m 0640 ${S}/settings.json ${D}${localstatedir}/lib/router-dashboard/settings.json
    chown -R 995:995 ${D}${localstatedir}/lib/router-dashboard
}

FILES:${PN} = "/www/pages \
               ${datadir}/router-dashboard \
               ${localstatedir}/lib/router-dashboard"

CONFFILES:${PN} = "${localstatedir}/lib/router-dashboard/settings.json"
