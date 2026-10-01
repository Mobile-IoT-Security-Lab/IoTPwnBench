#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
    char command[512];
    if (argc != 2) {
        fprintf(stderr, "usage: iotbench-cdiag <target>\n");
        return 2;
    }
    if (snprintf(command, sizeof(command), "printf 'probing %%s\\n' %s", argv[1]) >= (int)sizeof(command)) {
        fprintf(stderr, "target too long\n");
        return 2;
    }
    return system(command);
}
