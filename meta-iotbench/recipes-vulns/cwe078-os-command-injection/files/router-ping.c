/*
 * Router dashboard PoC helper.
 *
 * INTENTIONALLY VULNERABLE LAB CODE:
 * The user-controlled target is interpolated into a shell command.
 * Do not deploy outside an isolated, disposable test image.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
    char command[1024];

    if (argc != 2 || argv[1][0] == '\0') {
        fprintf(stderr, "usage: router-ping <target>\n");
        return 2;
    }

    /*
     * Vulnerability: shell metacharacters in argv[1] are not rejected.
     * This is deliberately included for the PoC and should be fixed with
     * direct execve()/posix_spawn() and strict IPv4 validation.
     */
    if (snprintf(command, sizeof(command), "ping -c 1 -W 2 %s", argv[1])
        >= (int)sizeof(command)) {
        fprintf(stderr, "target too long\n");
        return 2;
    }

    return system(command);
}
