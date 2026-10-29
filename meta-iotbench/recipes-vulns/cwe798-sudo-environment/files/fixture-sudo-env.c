/* INTENTIONALLY INSECURE SYNTHETIC FIXTURE. Never deploy.
 * One sudo environment-policy scenario. No command, library or path comes
 * from the environment. The public credential gates only a fixed response.
 */
#define _POSIX_C_SOURCE 200809L
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#ifndef IOTBENCH_SUDO_ENV_FIXTURE_ENABLED
#define IOTBENCH_SUDO_ENV_FIXTURE_ENABLED 0
#endif
#ifndef FIXTURE_MANIFEST
#define FIXTURE_MANIFEST "/usr/share/iotbench/sudo-environment/build-config"
#endif

#if IOTBENCH_SUDO_ENV_FIXTURE_ENABLED == 1
/* CWE-798: public, non-sensitive credential for this diagnostic only.
 * This is not an OS password and authenticates to no external service. */
static const char FIXTURE_PASSWORD[] = "Fixture-Sudo-Only-42";
static const char BUILD_CONFIG[] =
    "IOTBENCH_SUDO_ENV_TEST_ONLY_V1\nmode=fixture\nenabled=1\n";

static int fixture_build(void)
{
    char buffer[sizeof BUILD_CONFIG];
    struct stat metadata;
    int fd = open(FIXTURE_MANIFEST, O_RDONLY | O_NOFOLLOW | O_NONBLOCK);
    if (fd < 0)
        return 0;
    int valid = fstat(fd, &metadata) == 0 && S_ISREG(metadata.st_mode) &&
        metadata.st_uid == 0 && (metadata.st_mode & 022) == 0 &&
        metadata.st_size == (off_t)(sizeof BUILD_CONFIG - 1) &&
        read(fd, buffer, sizeof buffer) == (ssize_t)(sizeof BUILD_CONFIG - 1) &&
        memcmp(buffer, BUILD_CONFIG, sizeof BUILD_CONFIG - 1) == 0;
    close(fd);
    return valid;
}

static const char *setting(const char *name, const char *fallback)
{
    const char *value = getenv(name);
    return value ? value : fallback;
}
#endif

int main(int argc, char **argv)
{
#if IOTBENCH_SUDO_ENV_FIXTURE_ENABLED != 1
    (void)argc;
    (void)argv;
    fputs("DENIED fixture build required\n", stderr);
    return 77;
#else
    if (argc != 2 || strcmp(argv[1], "--fixture-test") != 0 ||
            geteuid() != 0 || !fixture_build()) {
        fputs("DENIED isolated fixture invocation required\n", stderr);
        return 77;
    }
    const char *mode = setting("FIXTURE_MODE", "status");
    const char *config = setting("FIXTURE_CONFIG", "public");
    const char *profile = setting("TEST_PROFILE", "baseline");
    if ((strcmp(mode, "status") != 0 && strcmp(mode, "diagnostic") != 0) ||
            (strcmp(profile, "baseline") != 0 && strcmp(profile, "boundary") != 0)) {
        fputs("DENIED unsupported synthetic setting\n", stderr);
        return 2;
    }
    int credential_matches = strcmp(config, FIXTURE_PASSWORD) == 0;
    if ((!credential_matches && strcmp(config, "public") != 0) ||
            (strcmp(mode, "diagnostic") == 0 && !credential_matches)) {
        fputs("DENIED synthetic credential\n", stderr);
        return 3;
    }
    puts("FIXTURE_EUID=0");
    printf("MODE=%s\nCONFIG=%s\nPROFILE=%s\nUNLISTED=%s\nRESULT=%s\n",
           mode, credential_matches ? "synthetic-fixed" : "public", profile,
           getenv("FIXTURE_UNLISTED") ? "present" : "absent",
           strcmp(mode, "diagnostic") == 0 ? "synthetic-diagnostic" : "nominal");
    return 0;
#endif
}
