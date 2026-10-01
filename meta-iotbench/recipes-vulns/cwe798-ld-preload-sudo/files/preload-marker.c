#include <stdio.h>
#include <unistd.h>

__attribute__((constructor))
static void mark_root_execution(void) {
    FILE *fp = fopen("/tmp/iotbench-ldpreload-root", "w");
    if (fp != NULL) {
        fprintf(fp, "preload constructor ran with uid=%ld euid=%ld\n", (long)getuid(), (long)geteuid());
        fclose(fp);
    }
}
