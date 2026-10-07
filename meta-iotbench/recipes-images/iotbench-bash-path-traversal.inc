# Keep the known-positive data/ escape while asserting outer lab containment.
ROOTFS_POSTPROCESS_COMMAND += "iotbench_bash_path_traversal_metadata; "

iotbench_bash_path_traversal_metadata() {
    fixture_dir="${IMAGE_ROOTFS}${datadir}/iotbench/bash-path-traversal"
    for fixture_helper in "${IMAGE_ROOTFS}${bindir}/iotbench-bash-read" \
        "${IMAGE_ROOTFS}${libdir}/iotbench/bash-path-traversal/fixture-confine.so"; do
        if [ "$(stat -c '%u:%g:%a' "$fixture_helper")" != "0:0:755" ]; then
            bbfatal "Bash fixture helper and confinement builtin must be ordinary root:root 0755"
        fi
    done
    for fixture_file in data/public.txt internal/private-fixture.txt; do
        if [ "$(stat -c '%u:%g:%a' "$fixture_dir/rootfs${datadir}/iotbench/bash-path-traversal/$fixture_file")" != "0:0:644" ]; then
            bbfatal "Bash fixture data must be root:root 0644"
        fi
    done
    if [ "$(find "$fixture_dir/rootfs" -type f | wc -l)" -ne 2 ] || \
        [ -n "$(find "$fixture_dir/rootfs" ! -type d ! -type f)" ]; then
        bbfatal "Bash fixture jail must contain only two synthetic files and their directories"
    fi
    cat "$fixture_dir/NOTICE" >> ${IMAGE_ROOTFS}${sysconfdir}/motd
}
