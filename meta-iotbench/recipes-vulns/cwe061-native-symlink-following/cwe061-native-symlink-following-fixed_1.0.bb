require recipes-vulns/cwe061-native-symlink-following/cwe061-native-symlink-following_1.0.bb

SUMMARY = "IoTBench corrected variant - native symlink following, CWE-61"
DESCRIPTION = "Corrected twin of the native symlink fixture. The final path component is opened with O_NOFOLLOW. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
