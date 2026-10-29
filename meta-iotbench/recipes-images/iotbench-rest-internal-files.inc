# One intentional path-handling flaw; both CWE identifiers describe that flow.
IOTBENCH_CWE = "CWE-22 CWE-73"
IOTBENCH_VULN_INSTALL = "cwe022-rest-internal-files"
IOTBENCH_BUILD_MODE ?= "production"
IOTBENCH_ENABLE_REST_FIXTURE ?= "0"
IOTBENCH_REST_LAYER := "${THISDIR}/.."

python iotbench_rest_fixture_guard() {
    import runpy
    policy = d.getVar('IOTBENCH_REST_LAYER') + '/recipes-vulns/cwe022-rest-internal-files/files/fixture-build.py'
    try:
        runpy.run_path(policy)['validate_build'](
            d.getVar('IOTBENCH_BUILD_MODE'),
            d.getVar('IOTBENCH_ENABLE_REST_FIXTURE'), d.getVar('MACHINE'))
    except ValueError as error:
        bb.fatal(str(error))
    expected = 'cwe022-rest-internal-files'
    if d.getVar('IOTBENCH_VULN_INSTALL') != expected:
        bb.fatal('REST fixtures must contain exactly one scenario package')
    extras = (d.getVar('IMAGE_INSTALL') or '').split()
    if any(p.startswith('cwe') and p != expected for p in extras):
        bb.fatal('Another vulnerability package cannot be mixed into REST fixtures')
}
do_rootfs[prefuncs] += "iotbench_rest_fixture_guard"
ROOTFS_POSTPROCESS_COMMAND += "iotbench_rest_fixture_metadata; "

python iotbench_rest_fixture_metadata() {
    import pathlib
    root = pathlib.Path(d.getVar('IMAGE_ROOTFS')) / (d.getVar('datadir').lstrip('/') + '/iotbench/rest-internal-files')
    for path in [root] + list(root.rglob('*')):
        mode = 0o755 if path.is_dir() or path.parent == root / 'bin' else 0o644
        if path == root / 'run':
            mode = 0o700
        if path.is_symlink() or path.stat().st_uid != 0 or path.stat().st_gid != 0 or path.stat().st_mode & 0o7777 != mode:
            bb.fatal('REST fixture must retain ordinary root-owned permissions')
    if (root / 'fs/.fixture-test-only').read_text() != 'IOTBENCH_REST_TEST_ONLY_V1\nmode=fixture\nenabled=1\n':
        bb.fatal('REST fixture requires its explicit test manifest')
    if list((root / 'run').iterdir()):
        bb.fatal('REST fixture must not have been started during image creation')
}
