/* Router dashboard ping helper, corrected variant of CWE-78. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* A target is a host name or an address made of letters, digits, dots and hyphens. */
static int valid_target(const char *target)
{
    if (target[0] == '-') return 0;
    for (; *target; ++target) {
        if (!((*target >= 'a' && *target <= 'z') || (*target >= 'A' && *target <= 'Z') ||
              (*target >= '0' && *target <= '9') || *target == '.' || *target == '-'))
            return 0;
    }
    return 1;
}

int main(int argc, char **argv) {
    if (argc != 2 || argv[1][0] == '\0') {
        fprintf(stderr, "usage: router-ping <target>\n");
        return 2;
    }

    if (!valid_target(argv[1])) {
        fprintf(stderr, "invalid target\n");
        return 2;
    }

    /* The target is passed as one argument and no shell is involved. */
    execlp("ping", "ping", "-c", "1", "-W", "2", argv[1], (char *)NULL);
    perror("ping");
    return 127;
}
