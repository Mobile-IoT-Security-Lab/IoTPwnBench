# One wildcard argument injection scenario; the related CWEs share this flow.
IOTBENCH_CWE = "CWE-88 CWE-78 CWE-269"
IOTBENCH_VULN_INSTALL = "cwe088-cronjob-wildcard-injection"
IOTBENCH_BUILD_MODE ?= "production"
IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE ?= "0"

python iotbench_cron_wildcard_fixture_guard() {
    import runpy
    policy = d.getVar('IOTBENCH_CRON_FIXTURE_LAYER') + '/recipes-vulns/cwe088-cronjob-wildcard-injection/files/fixture-build.py'
    try:
        runpy.run_path(policy)['validate_build'](
            d.getVar('IOTBENCH_BUILD_MODE'),
            d.getVar('IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE'), d.getVar('MACHINE'))
    except ValueError as error:
        bb.fatal(str(error))
}
# Resolve the layer location while THISDIR still names recipes-images.
IOTBENCH_CRON_FIXTURE_LAYER := "${THISDIR}/.."
do_rootfs[prefuncs] += "iotbench_cron_wildcard_fixture_guard"
ROOTFS_POSTPROCESS_COMMAND += "iotbench_cron_wildcard_fixture_metadata; "

iotbench_cron_wildcard_fixture_metadata() {
    fixture_root='${IMAGE_ROOTFS}${datadir}/iotbench/cronjob-wildcard-injection'
    for fixture_file in build-config bin/fixture-maintenance cron/vulnerable.crontab cron/secure.crontab; do
        fixture_mode=644
        [ "$fixture_file" != bin/fixture-maintenance ] || fixture_mode=755
        if [ "$(stat -c '%u:%g:%a' "$fixture_root/$fixture_file")" != "0:0:$fixture_mode" ]; then
            bbfatal "Cron fixture control files must retain ordinary root-owned permissions"
        fi
    done
    if [ "$(stat -c '%u:%g:%a' "$fixture_root/inbox")" != "988:988:750" ]; then
        bbfatal "Only fixturefiles may write the dedicated cron fixture inbox"
    fi
}
