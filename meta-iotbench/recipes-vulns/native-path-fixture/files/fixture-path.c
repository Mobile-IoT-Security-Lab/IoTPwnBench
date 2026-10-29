/* SPDX-License-Identifier: MIT
 * Synthetic read-only benchmark. Exactly one flaw is compiled per variant.
 * Runtime requires the disposable namespace runner; never install as a service.
 */
#define _GNU_SOURCE
#include <stdio.h>
#ifndef IOTBENCH_PATH_FIXTURE_ENABLED
#define IOTBENCH_PATH_FIXTURE_ENABLED 0
#endif
#if !IOTBENCH_PATH_FIXTURE_ENABLED
int main(void) { fputs("Native path fixture disabled\n", stderr); return 77; }
#else
#include <errno.h>
#include <fcntl.h>
#include <linux/capability.h>
#include <linux/magic.h>
#include <linux/openat2.h>
#include <signal.h>
#include <stdlib.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <sys/syscall.h>
#include <sys/time.h>
#include <sys/un.h>
#include <unistd.h>
#ifndef SYS_openat2
#define SYS_openat2 __NR_openat2
#endif
#if PATH_FIXTURE_CWE != 22 && PATH_FIXTURE_CWE != 20
#error "Select exactly one of PATH_FIXTURE_CWE=22 or 20"
#endif
#define PATH_LIMIT 255
#define FILE_LIMIT 4096

static int confined_open(int root, const char *path, int directory)
{
    struct open_how how = {
        .flags = O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK | O_NOCTTY,
        .resolve = RESOLVE_BENEATH | RESOLVE_NO_SYMLINKS | RESOLVE_NO_XDEV
    };
    if (directory) how.flags |= O_DIRECTORY;
    /* No fallback: kernels lacking openat2 must refuse this test. */
    return (int)syscall(SYS_openat2, root, path, &how, sizeof(how));
}

static int send_all(int fd, const char *data, size_t size)
{
    while (size) {
        ssize_t n = send(fd, data, size, MSG_NOSIGNAL);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return -1;
        data += n;
        size -= (size_t)n;
    }
    return 0;
}

static int receive_exact(int fd, void *buffer, size_t size)
{
    char *out = buffer;
    while (size) {
        ssize_t n = recv(fd, out, size, 0);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return -1;
        out += n;
        size -= (size_t)n;
    }
    return 0;
}

/* Source: two-byte big-endian length, 1..255 ASCII bytes, then write EOF.
 * Explicit-length checks reject NUL, controls, absolute paths and extra frames.
 */
static int request_path(int client, char file[PATH_LIMIT + 1])
{
    unsigned char header[2];
    if (receive_exact(client, header, sizeof(header))) return -1;
    size_t size = (size_t)header[0] * 256 + header[1];
    if (!size || size > PATH_LIMIT || receive_exact(client, file, size)) return -1;
    char extra;
    ssize_t n;
    do { n = recv(client, &extra, 1, 0); } while (n < 0 && errno == EINTR);
    if (n != 0 || file[0] == '/') return -1;
    for (size_t i = 0; i < size; ++i) {
        unsigned char c = (unsigned char)file[i];
        if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') ||
              c == '_' || c == '-' || c == '.' || c == '/')) return -1;
    }
    file[size] = '\0';
    return 0;
}

#if PATH_FIXTURE_CWE == 20
static int filename_policy(const char *file)
{
    /* Contract: [a-z][a-z0-9_-]{0,31}\.cfg, with no following characters.
     * Containment is independent: every slash is rejected before the sink.
     */
    if (strchr(file, '/') || file[0] < 'a' || file[0] > 'z') return 0;
    const char *dot = strchr(file, '.');
    if (!dot || dot - file > 32) return 0;
    for (const char *p = file; p < dot; ++p)
        if (!((*p >= 'a' && *p <= 'z') || (*p >= '0' && *p <= '9') ||
              *p == '_' || *p == '-')) return 0;
    /* INTENTIONAL CWE-20: extension prefix checked without end-of-string.
     * private.cfg.bak passes although it violates the documented contract.
     */
    return strncmp(dot, ".cfg", 4) == 0;
}
#endif

static const char *retrieve(int rootfd, const char *file, char *body, size_t *size)
{
    int input;
#if PATH_FIXTURE_CWE == 22
    char path[sizeof("allowed/") + PATH_LIMIT];
    /* INTENTIONAL CWE-22 (CWE-20 contributing): relative syntax validation
     * never checks parent components against the intended allowed/ boundary.
     * allowed/../sentinel.txt resolves outside allowed/, still inside fs/.
     */
    int n = snprintf(path, sizeof(path), "allowed/%s", file);
    if (n < 0 || (size_t)n >= sizeof(path)) return "ERR INVALID\n";
    input = confined_open(rootfd, path, 0); /* Read-only filesystem sink. */
#else
    if (!filename_policy(file)) return "ERR DENIED\n";
    /* rootfd is allowed/ itself, so the extension defect cannot escape it. */
    input = confined_open(rootfd, file, 0); /* Read-only filesystem sink. */
#endif
    if (input < 0) return errno == ENOENT ? "ERR MISSING\n" : "ERR DENIED\n";
    struct stat st;
    if (fstat(input, &st) || !S_ISREG(st.st_mode) || st.st_size < 0 ||
        st.st_size > FILE_LIMIT) {
        close(input);
        return "ERR DENIED\n";
    }
    *size = 0;
    while (*size < FILE_LIMIT) {
        ssize_t n = read(input, body + *size, FILE_LIMIT - *size);
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) { close(input); return "ERR DENIED\n"; }
        if (!n) break;
        *size += (size_t)n;
    }
    close(input);
    return NULL;
}

static void handle_request(int client, int rootfd)
{
    char file[PATH_LIMIT + 1], body[FILE_LIMIT], header[40];
    size_t size = 0;
    const char *error = "ERR INVALID\n";
    if (!request_path(client, file)) error = retrieve(rootfd, file, body, &size);
    if (error) { (void)send_all(client, error, strlen(error)); return; }
    int n = snprintf(header, sizeof(header), "OK %zu\n", size);
    if (n > 0 && (size_t)n < sizeof(header) && !send_all(client, header, (size_t)n))
        (void)send_all(client, body, size);
}

static int isolated(void)
{
    struct statfs fs;
    struct statvfs flags;
    struct __user_cap_header_struct header = {_LINUX_CAPABILITY_VERSION_3, 0};
    struct __user_cap_data_struct caps[2] = {{0}, {0}};
    if (getuid() != 1000 || geteuid() != 1000 || getgid() != 1000 ||
        prctl(PR_GET_NO_NEW_PRIVS, 0, 0, 0, 0) != 1 ||
        syscall(SYS_capget, &header, caps) ||
        caps[0].effective || caps[1].effective || caps[0].permitted || caps[1].permitted ||
        statfs("/", &fs) || fs.f_type != TMPFS_MAGIC ||
        statvfs("/", &flags) || !(flags.f_flag & ST_RDONLY)) return 0;
    int fd = open("/run/iotbench-path-isolated", O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    char marker[32] = {0};
    const char expected[] = "IOTBENCH_PATH_ISOLATED_V1\n";
    if (fd < 0) return 0;
    ssize_t n = read(fd, marker, sizeof(marker));
    close(fd);
    return n == (ssize_t)sizeof(expected) - 1 && !memcmp(marker, expected, sizeof(expected) - 1);
}

int main(int argc, char **argv)
{
    if (argc != 2 || strcmp(argv[1], "--isolated-fixture")) return 77;
    if (!isolated()) { fputs("Requires the isolated test runner\n", stderr); return 77; }
    int fsfd = open("/fixture/fs", O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (fsfd < 0) { perror("fixture fs"); return 77; }
    /* Probe kernel confinement before opening a listener, also on CWE-22. */
    int allowed = confined_open(fsfd, "allowed", 1);
    if (allowed < 0) { perror("fixture openat2"); close(fsfd); return 77; }
#if PATH_FIXTURE_CWE == 22
    close(allowed);
    int rootfd = fsfd;
#else
    close(fsfd);
    int rootfd = allowed;
#endif
    struct sockaddr_un address = {.sun_family = AF_UNIX};
    memcpy(address.sun_path, "/run/path.sock", sizeof("/run/path.sock"));
    umask(0077);
    int listener = socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
    /* Never unlink an existing pathname. The runner owns socket cleanup. */
    if (listener < 0 || bind(listener, (struct sockaddr *)&address, sizeof(address)) ||
        listen(listener, 4)) {
        perror("fixture Unix listener");
        if (listener >= 0) close(listener);
        close(rootfd);
        return 77;
    }
    signal(SIGPIPE, SIG_IGN);
    puts("fixture-ready unix-only");
    fflush(stdout);
    for (;;) {
        int client = accept4(listener, NULL, NULL, SOCK_CLOEXEC);
        if (client < 0) { if (errno == EINTR) continue; break; }
        struct timeval timeout = {.tv_sec = 1, .tv_usec = 0};
        if (!setsockopt(client, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) &&
            !setsockopt(client, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout)))
            handle_request(client, rootfd);
        close(client);
    }
    close(listener);
    close(rootfd);
    return 0;
}
#endif
