#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: iotbench-cdiag <target>\n");
        return 2;
    }
    /* The target is printed as data and no shell is involved. */
    printf("probing %s\n", argv[1]);
    return 0;
}
