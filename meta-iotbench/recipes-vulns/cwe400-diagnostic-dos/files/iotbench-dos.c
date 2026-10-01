#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv) {
    long mb = argc > 1 ? strtol(argv[1], NULL, 10) : 1;
    size_t bytes = (size_t)mb * 1024u * 1024u;
    char *buf = malloc(bytes);
    if (buf == NULL) {
        fprintf(stderr, "allocation failed for %ld MB\n", mb);
        return 1;
    }
    memset(buf, 0x41, bytes);
    printf("allocated and touched %ld MB\n", mb);
    sleep(2);
    free(buf);
    return 0;
}
