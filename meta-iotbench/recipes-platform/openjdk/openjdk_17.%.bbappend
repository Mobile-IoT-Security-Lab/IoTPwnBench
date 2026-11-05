# Docker uses a Linux userspace even when its host kernel reports WSL.  OpenJDK
# otherwise treats config.guess's *-wsl triplet as a Windows build and invokes
# Windows-only path conversion tools during configure.
OPENJDK_CONF_ENV:append = " ac_cv_build=${BUILD_ARCH}-pc-linux-gnu"
