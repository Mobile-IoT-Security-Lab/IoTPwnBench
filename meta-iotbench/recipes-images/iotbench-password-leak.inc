IOTBENCH_CWE = "CWE-798"
# A corrected twin sets IOTBENCH_TWIN to 1. It installs the corrected variant of the module.
IOTBENCH_TWIN ?= "0"
IOTBENCH_TWIN_SUFFIX = "${@'-fixed' if d.getVar('IOTBENCH_TWIN') == '1' else ''}"
IOTBENCH_VULN_INSTALL = "cwe798-password-leak-${IOTBENCH_PASSWORD_LEAK_VARIANT}${IOTBENCH_TWIN_SUFFIX}"
IOTBENCH_BUILD_MODE ?= "production"
IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE ?= "0"
IOTBENCH_PASSWORD_LEAK_LAYER := "${THISDIR}/.."

python iotbench_password_leak_guard() {
    import runpy
    policy = d.getVar('IOTBENCH_PASSWORD_LEAK_LAYER') + '/recipes-vulns/cwe798-password-leak/files/fixture-lib.py'
    try:
        runpy.run_path(policy)['validate_build'](
            d.getVar('IOTBENCH_BUILD_MODE'),
            d.getVar('IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE'), d.getVar('MACHINE'),
            d.getVar('IOTBENCH_PASSWORD_LEAK_VARIANT'))
    except ValueError as error:
        bb.fatal(str(error))
    expected = 'cwe798-password-leak-' + d.getVar('IOTBENCH_PASSWORD_LEAK_VARIANT') + d.getVar('IOTBENCH_TWIN_SUFFIX')
    if d.getVar('IOTBENCH_VULN_INSTALL') != expected:
        bb.fatal('Password Leak images must contain exactly one scenario package')
    extras = (d.getVar('IMAGE_INSTALL') or '').split()
    if any(p.startswith('cwe') and p != expected for p in extras):
        bb.fatal('Another vulnerability package cannot be mixed into Password Leak images')
}
do_rootfs[prefuncs] += "iotbench_password_leak_guard"
ROOTFS_POSTPROCESS_COMMAND += "iotbench_password_leak_metadata; "

python iotbench_password_leak_metadata() {
    import json
    import pathlib
    import runpy
    rootfs = pathlib.Path(d.getVar('IMAGE_ROOTFS'))
    base = rootfs / (d.getVar('datadir').lstrip('/') + '/iotbench/password-leak')
    variant = d.getVar('IOTBENCH_PASSWORD_LEAK_VARIANT')
    if sorted(p.name for p in base.iterdir()) != [variant]:
        bb.fatal('Exactly one Password Leak fixture may be installed')
    root = base / variant
    native_auth = root / 'fixture-auth'
    for path in [root] + list(root.rglob('*')):
        mode = 0o755 if path.is_dir() or path == native_auth else 0o644
        if path.is_symlink() or path.stat().st_uid != 0 or path.stat().st_gid != 0 or path.stat().st_mode & 0o7777 != mode:
            bb.fatal('Password Leak fixture must retain ordinary root-owned permissions')
    if not native_auth.is_file() or native_auth.read_bytes()[:4] != b'\x7fELF':
        bb.fatal('Password Leak fixture must contain its native local authenticator')
    lib = runpy.run_path(str(root / 'fixture-lib.py'))
    findings = lib['scan'](root)
    expected = json.loads((root / 'expected-findings.json').read_text())
    import hashlib
    actual = [dict(path=(root.relative_to(rootfs) / f['path']).as_posix(), line=f['line'], field=f['field'], encoding=f['encoding'],
                   sha256=hashlib.sha256(f['value'].encode()).hexdigest()) for f in findings]
    wanted = [{k: e[k] for k in ('path', 'line', 'field', 'encoding', 'sha256')} for e in expected]
    if actual != wanted:
        bb.fatal('Password Leak rootfs differs from expected synthetic finding')
    if any(f['value'].encode() in native_auth.read_bytes() for f in findings):
        bb.fatal('Password Leak authenticator must read, not embed, the synthetic credential')
}
