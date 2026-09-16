FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"

# The base recipe installs this file. Supplying it through FILESEXTRAPATHS keeps
# ownership of /etc/lighttpd/lighttpd.conf with the lighttpd package.
SRC_URI += "file://lighttpd.conf"
