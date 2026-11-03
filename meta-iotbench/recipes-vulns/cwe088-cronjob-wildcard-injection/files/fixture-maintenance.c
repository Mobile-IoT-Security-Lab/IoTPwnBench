/* Diagnostic argument parser only. No commands, operand reads or file writes. */
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <string.h>

#if !defined(IOTBENCH_CRON_WILDCARD_FIXTURE_ENABLED) || IOTBENCH_CRON_WILDCARD_FIXTURE_ENABLED != 1
int main(void)
{
    fputs("fixture-disabled\n", stderr);
    return 77;
}
#else
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

#ifndef FIXTURE_ROOT
#error "Explicit fixture root required"
#endif

static int fixture_context(void)
{
    const char expected[] = "IOTBENCH_CRON_WILDCARD_TEST_ONLY_V1\nmode=fixture\nenabled=1\n";
    char marker[sizeof expected];
    struct stat current, inbox, manifest;
    int fd = open(FIXTURE_ROOT "/build-config", O_RDONLY | O_NOFOLLOW);
    if (fd < 0)
        return 0;
    int valid = fstat(fd, &manifest) == 0 && S_ISREG(manifest.st_mode) &&
        !(manifest.st_mode & 0022) &&
        read(fd, marker, sizeof marker) == (ssize_t)(sizeof expected - 1) &&
        memcmp(marker, expected, sizeof expected - 1) == 0;
    close(fd);
    return valid && stat(".", &current) == 0 &&
        lstat(FIXTURE_ROOT "/inbox", &inbox) == 0 && S_ISDIR(inbox.st_mode) &&
        current.st_dev == inbox.st_dev && current.st_ino == inbox.st_ino;
}

/* Encode untrusted filenames as JSON data, including control characters. */
static void json_string(const char *value)
{
    putchar('"');
    for (const unsigned char *p = (const unsigned char *)value; *p; ++p) {
        if (*p == '"' || *p == '\\')
            printf("\\%c", *p);
        else if (*p < 32 || *p >= 127)
            printf("\\u%04x", (unsigned int)*p);
        else
            putchar(*p);
    }
    putchar('"');
}

int main(int argc, char **argv)
{
    if (argc < 2 || strcmp(argv[1], "--fixture-test") || !fixture_context()) {
        fputs("fixture-context-required\n", stderr);
        return 77;
    }
    unsigned options = 0, operands = 0;
    int separated = 0, diagnostic = 0;
    puts("{\"context\":\"root-cron-maintenance\",\"cron_runas\":\"root\",\"helper_changes_uid\":false}");
    for (int i = 2; i < argc; ++i) {
        if (!separated && strcmp(argv[i], "--") == 0) {
            separated = 1;
            puts("{\"kind\":\"separator\"}");
            continue;
        }
        /* Intentional sink: a wildcard-expanded filename can enter this branch. */
        int option = !separated && argv[i][0] == '-' && argv[i][1] != '\0';
        if (option) {
            ++options;
            if (strcmp(argv[i], "--fixture-diagnostic") == 0)
                diagnostic = 1;
        } else {
            ++operands;
        }
        printf("{\"kind\":\"%s\",\"argument\":", option ? "option" : "operand");
        json_string(argv[i]);
        puts("}");
    }
    printf("{\"options\":%u,\"operands\":%u,\"result\":\"%s\"}\n",
           options, operands, diagnostic ? "synthetic-diagnostic" : "nominal");
    return 0;
}
#endif
