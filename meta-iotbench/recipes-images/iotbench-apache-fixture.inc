# Dedicated minimal firmware: device identity/peripheral specification, one CWE,
# Apache, and the unprivileged namespace test runner. No native device daemons.
IOTBENCH_BUILD_MODE ?= "production"
IOTBENCH_ENABLE_APACHE_FIXTURE ?= "0"
IOTBENCH_APACHE_LAYER := "${THISDIR}/.."
IOTBENCH_VULN_INSTALL = "apache-web-fixture-cwe${APACHE_FIXTURE_CWE}"
IOTBENCH_CWE = "CWE-${APACHE_FIXTURE_CWE}"
IOTBENCH_DEVICE_INSTALL = ""
IMAGE_INSTALL = "packagegroup-core-boot ${IOTBENCH_VULN_INSTALL}"

python iotbench_apache_guard() {
    import runpy
    policy = d.getVar('IOTBENCH_APACHE_LAYER') + '/recipes-vulns/apache-web-fixture/files/fixture-build.py'
    runpy.run_path(policy)['validate_build'](d.getVar('IOTBENCH_BUILD_MODE'),
        d.getVar('IOTBENCH_ENABLE_APACHE_FIXTURE'), d.getVar('MACHINE'))
    expected = 'apache-web-fixture-cwe' + d.getVar('APACHE_FIXTURE_CWE')
    if d.getVar('IOTBENCH_VULN_INSTALL') != expected or set(d.getVar('IMAGE_INSTALL').split()) != {'packagegroup-core-boot', expected}:
        bb.fatal('Apache fixture images require exactly one variant and no other applications')
}
do_rootfs[prefuncs] += "iotbench_apache_guard"
ROOTFS_POSTPROCESS_COMMAND += "iotbench_apache_metadata; "

python iotbench_apache_metadata() {
    import pathlib
    import shutil
    root = pathlib.Path(d.getVar('IMAGE_ROOTFS'))
    device = d.getVar('IOTBENCH_DEVICE')
    source = pathlib.Path(d.getVar('IOTBENCH_APACHE_LAYER')) / 'recipes-devices' / device / 'files'
    target = root / 'etc/iotbench'
    target.mkdir(parents=True, exist_ok=True)
    for name in ('device.conf', 'peripherals.conf'):
        shutil.copyfile(source / name, target / name)
    # Never boot the distribution's root-started Apache service or use its config.
    for pattern in ('etc/rc*.d/*apache2', 'etc/init.d/apache2'):
        for path in root.glob(pattern):
            path.unlink()
    mask = root / 'etc/systemd/system/apache2.service'
    mask.parent.mkdir(parents=True, exist_ok=True)
    if mask.exists() or mask.is_symlink():
        mask.unlink()
    mask.symlink_to('/dev/null')
    (root / 'etc/apache2').mkdir(parents=True, exist_ok=True)
    (root / 'etc/apache2/httpd.conf').write_text('Error "Use the unprivileged isolated Apache fixture runner"\n')
    base = root / d.getVar('datadir').lstrip('/') / 'iotbench/apache-fixture'
    if list(base.glob('variants/*')) or not (base / 'scenario.py').exists():
        bb.fatal('Only the selected Apache scenario may be installed')
    # Reject accidental additional vulnerability packages from dependencies.
    manifest = pathlib.Path(d.getVar('IMAGE_MANIFEST'))
    if manifest.exists():
        packages = [line.split()[0] for line in manifest.read_text().splitlines() if line.split()]
        variants = [p for p in packages if p.startswith(('cwe', 'apache-web-fixture-cwe'))]
        if variants != ['apache-web-fixture-cwe' + d.getVar('APACHE_FIXTURE_CWE')]:
            bb.fatal('Unexpected vulnerability packages in Apache fixture image')
}
