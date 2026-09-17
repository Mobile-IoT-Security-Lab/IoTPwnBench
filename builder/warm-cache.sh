#!/bin/bash
# Fill the shared cache (downloads and sstate) without exporting any firmware.
#   WARM_MACHINES       machines to prepare (default: YOCTO_MACHINE)
#   WARM_TARGETS        targets to build (default: core-image-minimal)
#   WARM_FETCH_TARGETS  extra targets whose sources are only downloaded
set -eo pipefail

WARM_TARGETS="${WARM_TARGETS:-core-image-minimal}"

for machine in ${WARM_MACHINES:-${YOCTO_MACHINE:-qemuarm64}}; do
    (
        YOCTO_MACHINE="${machine}"
        source /opt/yocto/yocto-env.sh
        bitbake --runall=fetch ${WARM_TARGETS} ${WARM_FETCH_TARGETS:-}
        bitbake ${WARM_TARGETS}
    )
done
