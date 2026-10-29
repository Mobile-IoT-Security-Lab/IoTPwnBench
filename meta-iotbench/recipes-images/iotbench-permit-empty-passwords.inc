# Explicit opt-in, configuration-only synthetic image family.
IOTBENCH_CWE = "CWE-521"
IOTBENCH_VULN_INSTALL = "cwe521-permit-empty-passwords"

# Do not inherit password-relaxing development features from local.conf.
IMAGE_FEATURES:remove = "debug-tweaks allow-empty-password empty-root-password allow-root-login"
EXTRA_IMAGE_FEATURES:remove = "debug-tweaks allow-empty-password empty-root-password allow-root-login"

# Fail dependency resolution if an SSH daemon is requested by another feature.
PACKAGE_EXCLUDE += "openssh-sshd dropbear"
BAD_RECOMMENDATIONS += "openssh-sshd dropbear"

IOTBENCH_EMPTY_PASSWORDS_VALIDATOR := "${THISDIR}/../recipes-vulns/cwe521-permit-empty-passwords/files/validate_config.py"
do_rootfs[file-checksums] += "${IOTBENCH_EMPTY_PASSWORDS_VALIDATOR}:True"
ROOTFS_POSTPROCESS_COMMAND += "iotbench_validate_empty_passwords; "

python iotbench_validate_empty_passwords() {
    import runpy
    validator = runpy.run_path(d.getVar('IOTBENCH_EMPTY_PASSWORDS_VALIDATOR'))
    try:
        validator['validate_rootfs'](d.getVar('IMAGE_ROOTFS'))
    except (AssertionError, OSError, ValueError) as error:
        bb.fatal('Unsafe or invalid configuration-only SSH fixture: %s' % error)
}
