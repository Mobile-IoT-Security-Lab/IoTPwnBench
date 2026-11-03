#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Corrected variant of CWE-416. The authorization object is released only after
 * its last use and the pointer is cleared, so nothing reads a freed object. */
int main(int argc, char **argv) {
    char *session = malloc(64);
    if (session == NULL) {
        return 1;
    }
    strcpy(session, "role=user;device=router");

    char *replacement = malloc(64);
    if (replacement == NULL) {
        free(session);
        return 1;
    }
    snprintf(replacement, 64, "%s", argc > 1 ? argv[1] : "role=user");

    printf("authorization object: %s\n", session);
    if (strstr(session, "role=admin") != NULL) {
        puts("ACCESS GRANTED via freed object reuse");
    } else {
        puts("access denied");
    }
    free(session);
    session = NULL;
    free(replacement);
    return 0;
}
