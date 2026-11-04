require recipes-vulns/cwe022-rest-internal-files/cwe022-rest-internal-files_1.0.bb

SUMMARY = "IoTBench corrected variant - REST internal files, CWE-22/CWE-73"
DESCRIPTION = "Corrected twin of the REST internal file fixture. Both binaries are built with the traversal control enabled. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"

do_compile() {
    ${CC} ${CPPFLAGS} ${CFLAGS} ${LDFLAGS} -std=c11 -Wall -Wextra -Werror \
        -DIOTBENCH_REST_FIXTURE_ENABLED=1 -DREST_SECURE_CONTROL=1 \
        -DFIXTURE_BASE='"${FIXTURE_BASE}"' \
        ${S}/fixture-rest.c -o ${B}/fixture-rest
    ${CC} ${CPPFLAGS} ${CFLAGS} ${LDFLAGS} -std=c11 -Wall -Wextra -Werror \
        -DIOTBENCH_REST_FIXTURE_ENABLED=1 -DREST_SECURE_CONTROL=1 \
        -DFIXTURE_BASE='"${FIXTURE_BASE}"' \
        ${S}/fixture-rest.c -o ${B}/fixture-rest-secure
}
