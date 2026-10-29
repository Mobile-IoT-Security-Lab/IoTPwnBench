SUMMARY = "IoTBench synthetic cron wildcard argument injection (CWE-88)"
DESCRIPTION = "One inert test cron schedule and a diagnostic-only native helper. Related modeled boundaries: CWE-78 and CWE-269. Explicit fixture builds only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
SRC_URI = "file://LICENSE file://NOTICE file://ground-truth.json \
           file://fixture-maintenance.c file://fixture-build.py file://fixture-runner.py \
           file://vulnerable.crontab.in file://secure.crontab.in"
S = "${UNPACKDIR}"

inherit useradd python3native
DEPENDS += "virtual/libc"
RDEPENDS:${PN} = "python3-core python3-modules"
USERADD_PACKAGES = "${PN}"
GROUPADD_PARAM:${PN} = "--system --gid 988 fixturefiles"
USERADD_PARAM:${PN} = "--system --uid 988 --gid fixturefiles --home-dir /nonexistent --no-create-home --shell /bin/false --password '!' fixturefiles"
IOTBENCH_BUILD_MODE ?= "production"
IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE ?= "0"
FIXTURE_ROOT = "${datadir}/iotbench/cronjob-wildcard-injection"

python __anonymous() {
    import runpy
    policy = d.getVar('THISDIR') + '/files/fixture-build.py'
    bb.parse.mark_dependency(d, policy)
    try:
        runpy.run_path(policy)['validate_build'](
            d.getVar('IOTBENCH_BUILD_MODE'),
            d.getVar('IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE'), d.getVar('MACHINE'))
    except ValueError as error:
        raise bb.parse.SkipRecipe(str(error))
}

do_compile[vardeps] += "IOTBENCH_BUILD_MODE IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE MACHINE"
do_compile() {
    ${CC} ${CPPFLAGS} ${CFLAGS} ${LDFLAGS} -std=c11 -Wall -Wextra -Werror \
        -DIOTBENCH_CRON_WILDCARD_FIXTURE_ENABLED=1 \
        -DFIXTURE_ROOT='"${FIXTURE_ROOT}"' \
        ${S}/fixture-maintenance.c -o ${B}/fixture-maintenance
}

do_install[vardeps] += "IOTBENCH_BUILD_MODE IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE MACHINE"
do_install() {
    ${PYTHON} ${S}/fixture-build.py --output ${D} --target-paths \
        --binary ${B}/fixture-maintenance --datadir '${datadir}' \
        --mode '${IOTBENCH_BUILD_MODE}' \
        --enable '${IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE}' --machine '${MACHINE}'
    chown fixturefiles:fixturefiles ${D}${FIXTURE_ROOT}/inbox
    chown fixturefiles:fixturefiles ${D}${FIXTURE_ROOT}/inbox/*.record
}

# Everything, including the ELF, inert crontabs and logs, stays in one tree.
# No cron dependency, startup hook, sudo rule, capabilities or setuid executable.
FILES:${PN} = "${FIXTURE_ROOT}"
