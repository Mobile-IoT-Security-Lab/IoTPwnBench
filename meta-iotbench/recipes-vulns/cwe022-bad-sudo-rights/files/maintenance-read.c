/* INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT
 * The sudo rule and this lexical prefix check intentionally accept ../.
 * chroot is a separate lab containment boundary around synthetic files;
 * it does NOT enforce the intended data/ authorization boundary.
 * No shell, subprocess, writes, networking, or setuid file mode is used. */
#define _DEFAULT_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#ifndef FIXTURE_ROOT
#define FIXTURE_ROOT "/usr/share/iotbench/bad-sudo-rights"
#endif

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "Usage: iotbench-maintenance-read FILE\n");
        return 2;
    }
    const char prefix[] = FIXTURE_ROOT "/data/";
    if (strncmp(argv[1], prefix, sizeof(prefix) - 1) != 0 ||
        strlen(argv[1]) > 240) {
        fprintf(stderr, "Expected a fixture data/ path up to 240 bytes\n");
        return 2;
    }
    if (geteuid() != 0) {
        fprintf(stderr, "Run through the fixture sudo rule\n");
        return 1;
    }
    /* Contain every read in a root-owned, non-writable synthetic tree. */
    if (chroot(FIXTURE_ROOT) != 0 || chdir("/") != 0) {
        perror("fixture confinement");
        return 1;
    }
    /* INTENTIONAL CWE-22: no canonicalization or restriction to /data/.
     * /data/../private/root-only.conf resolves outside the intended directory.
     * Removing only FIXTURE_ROOT retains the unvalidated /data/../ path. */
    int fd = open(argv[1] + sizeof(FIXTURE_ROOT) - 1,
                  O_RDONLY | O_NONBLOCK | O_NOFOLLOW);
    if (fd < 0) {
        perror("open");
        return 1;
    }
    struct stat st;
    if (fstat(fd, &st) < 0 || !S_ISREG(st.st_mode) || st.st_size > 65536) {
        fprintf(stderr, "Only regular files up to 65536 bytes are supported\n");
        close(fd);
        return 1;
    }
    printf("READER_EUID=%lu\n", (unsigned long)geteuid());
    char buf[4096];
    size_t remaining = 65536;
    while (remaining) {
        ssize_t n = read(fd, buf, remaining < sizeof(buf) ? remaining : sizeof(buf));
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) { perror("read"); close(fd); return 1; }
        if (n == 0) break;
        if (fwrite(buf, 1, (size_t)n, stdout) != (size_t)n) { close(fd); return 1; }
        remaining -= (size_t)n;
    }
    close(fd);
    return fflush(stdout) == 0 ? 0 : 1;
}
