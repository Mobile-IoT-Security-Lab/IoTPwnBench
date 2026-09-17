# Set up the BitBake environment in /workdir/build.
# Usage: source /opt/yocto/yocto-env.sh
#   YOCTO_MACHINE  target machine (default: qemuarm64)
#   YOCTO_LAYERS   layers to enable, relative to /opt/yocto/layers

# MACHINE is in BB_ENV_PASSTHROUGH_ADDITIONS, so it overrides local.conf.
export MACHINE="${YOCTO_MACHINE:-qemuarm64}"
source /opt/yocto/layers/openembedded-core/oe-init-build-env /workdir/build > /dev/null

cp /opt/yocto/site.conf conf/site.conf
cat > conf/bblayers.conf <<BBLAYERS
LCONF_VERSION = "7"
BBPATH = "\${TOPDIR}"
BBFILES ?= ""
BBLAYERS = "$(printf '/opt/yocto/layers/%s ' ${YOCTO_LAYERS:-openembedded-core/meta})"
BBLAYERS
