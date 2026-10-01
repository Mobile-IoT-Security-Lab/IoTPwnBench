#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
    char *session = malloc(64);
    if (session == NULL) {
        return 1;
    }
    strcpy(session, "role=user;device=router");
    char *stale = session;
    free(session);

    char *replacement = malloc(64);
    if (replacement == NULL) {
        return 1;
    }
    snprintf(replacement, 64, "%s", argc > 1 ? argv[1] : "role=user");

    printf("stale authorization object: %s\n", stale);
    if (strstr(stale, "role=admin") != NULL) {
        puts("ACCESS GRANTED via freed object reuse");
    } else {
        puts("access denied");
    }
    free(replacement);
    return 0;
}
