# Upstream's bootstrap archive is x86_64-only. Support both builder hosts.
OPENJDK_BOOT_ARCH = "${@{'x86_64': 'x64', 'aarch64': 'aarch64'}.get(d.getVar('BUILD_ARCH'), 'unsupported')}"
OPENJDK_BIN_NAME = "OpenJDK${PV_MAJOR}U-jdk_${OPENJDK_BOOT_ARCH}_linux_hotspot_${@d.getVar('PV').replace('+', '_')}.tar.gz"
SRC_URI[sha256sum] = "${@'457b57af8f9c93ec39080bb8c764f559dc8c89a6da1a39d718a400b7890d3e41' if d.getVar('BUILD_ARCH') == 'aarch64' else '3808d1d15e3ec6bd5b84057fb5d84c33d8a1536a258146bcea2e603fc726e08e'}"
