# SSH policy and read-only synthetic dashboard diagnostic image family.
IOTBENCH_CWE = "CWE-521"
# A corrected twin sets IOTBENCH_TWIN to 1. It installs the corrected variant of the module.
IOTBENCH_TWIN ?= "0"
IOTBENCH_TWIN_SUFFIX = "${@'-fixed' if d.getVar('IOTBENCH_TWIN') == '1' else ''}"
IOTBENCH_VULN_INSTALL = "cwe521-permit-empty-passwords${IOTBENCH_TWIN_SUFFIX}"

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
        validator['validate_rootfs'](d.getVar('IMAGE_ROOTFS'), 'no' if d.getVar('IOTBENCH_TWIN') == '1' else 'yes')
    except (AssertionError, OSError, ValueError) as error:
        bb.fatal('Unsafe or invalid configuration-only SSH fixture: %s' % error)
}
