/* SPDX-License-Identifier: GPL-3.0-or-later
 * Safe process containment for the Bash research fixture. This module has no
 * main(), accepts no input, constructs no user-controlled path, and reads no
 * files. The vulnerability is exclusively in iotbench-bash-read.
 */
#define _DEFAULT_SOURCE
#include "config.h"
#include "builtins.h"
#include <grp.h>
#include <stdio.h>
#include <sys/prctl.h>
#include <unistd.h>

#ifndef FIXTURE_JAIL
#error "FIXTURE_JAIL must be the fixed firmware fixture root"
#endif

static int fixture_confine_builtin(WORD_LIST *list)
{
    if (list != NULL || geteuid() != 0) {
        fprintf(stderr, "Fixture containment requires the guest root console and no arguments\n");
        return 1;
    }
    /* Bash and this module are already loaded. The new root needs no binaries,
     * libraries, device nodes, symlinks, /proc, or external bind mounts.
     * ../ remains unrestricted inside it, including data/ -> internal/.
     */
    if (chroot(FIXTURE_JAIL) != 0 || chdir("/") != 0 ||
        setgroups(0, NULL) != 0 || setgid(990) != 0 || setuid(990) != 0 ||
        prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0) {
        perror("fixture containment");
        /* Never return to Bash after a partially completed confinement. */
        _exit(2);
    }
    return 0;
}

static char * const fixture_confine_doc[] = {
    "Enter the fixed synthetic fixture root and permanently drop privileges.",
    "No arguments; does not validate the intended data/ directory boundary.",
    NULL
};

struct builtin fixture_confine_struct = {
    "fixture_confine", fixture_confine_builtin, BUILTIN_ENABLED,
    fixture_confine_doc, "fixture_confine", NULL
};
