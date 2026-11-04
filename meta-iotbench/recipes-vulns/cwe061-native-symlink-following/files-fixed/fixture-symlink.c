/* SPDX-License-Identifier: MIT
 * Synthetic read-only CWE-61 benchmark (broader CWE-59). Exactly one defect.
 * Runtime requires the disposable namespace runner; never install as a service.
 */
#define _GNU_SOURCE
#include <stdio.h>
#ifndef IOTBENCH_SYMLINK_FIXTURE_ENABLED
#define IOTBENCH_SYMLINK_FIXTURE_ENABLED 0
#endif
#if !IOTBENCH_SYMLINK_FIXTURE_ENABLED
int main(void) { fputs("Native symlink fixture disabled\n", stderr); return 77; }
#else
#include <errno.h>
#include <fcntl.h>
#include <linux/capability.h>
#include <linux/magic.h>
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
#define FILE_LIMIT 4096

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

/* The interface accepts exactly READ, never a filename or directory component. */
static int request_read(int client)
{
    unsigned char wire[6];
    if (receive_exact(client, wire, sizeof(wire))) return -1;
    const unsigned char expected[] = {0, 4, 'R', 'E', 'A', 'D'};
    if (memcmp(wire, expected, sizeof(expected))) return -1;
    char extra;
    ssize_t n;
    do { n = recv(client, &extra, 1, 0); } while (n < 0 && errno == EINTR);
    return n == 0 ? 0 : -1;
}

static const char *retrieve(int rootfd, char *body, size_t *size)
{
    /* POLICY: public.cfg must itself be an ordinary file in allowed/.
     * Corrected CWE-61 (broader CWE-59): O_NOFOLLOW on the final component
     * makes openat refuse a pre-established link instead of following it.
     */
    int input = openat(rootfd, "public.cfg", O_RDONLY | O_CLOEXEC | O_NONBLOCK | O_NOCTTY | O_NOFOLLOW);
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
    char body[FILE_LIMIT], header[40];
    size_t size = 0;
    const char *error = "ERR INVALID\n";
    if (!request_read(client)) error = retrieve(rootfd, body, &size);
    if (error) { (void)send_all(client, error, strlen(error)); return; }
    int n = snprintf(header, sizeof(header), "OK %zu\n", size);
    if (n > 0 && (size_t)n < sizeof(header) && !send_all(client, header, (size_t)n))
        (void)send_all(client, body, size);
}

/* The existing isolation launcher creates one fixed state in its disposable
 * tmpfs, then passes its name here. This one-shot terminal entry invokes the
 * same retrieve() sink as the Unix socket service, without a Python client. */
static int manual_state(int rootfd, const char *mode)
{
    struct stat entry;
    if (fstatat(rootfd, "public.cfg", &entry, AT_SYMLINK_NOFOLLOW)) return 0;
    if (!strcmp(mode, "ordinary")) return S_ISREG(entry.st_mode);
    if (!strcmp(mode, "symlink") && S_ISLNK(entry.st_mode)) {
        char target[sizeof("../sentinel.txt")];
        ssize_t n = readlinkat(rootfd, "public.cfg", target, sizeof(target));
        return n == (ssize_t)sizeof(target) - 1 &&
               !memcmp(target, "../sentinel.txt", sizeof(target) - 1);
    }
    return 0;
}

static int handle_manual_request(int rootfd, const char *mode)
{
    char body[FILE_LIMIT], header[40];
    size_t size = 0;
    const char *error = "ERR INVALID\n";
    if (manual_state(rootfd, mode)) error = retrieve(rootfd, body, &size);
    if (error) return fputs(error, stdout) == EOF ? 77 : 0;
    int n = snprintf(header, sizeof(header), "OK %zu\n", size);
    if (n <= 0 || (size_t)n >= sizeof(header) ||
        fwrite(header, 1, (size_t)n, stdout) != (size_t)n ||
        fwrite(body, 1, size, stdout) != size || fflush(stdout) == EOF)
        return 77;
    return 0;
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
    int manual = argc == 4 && !strcmp(argv[1], "--isolated-fixture") &&
                 !strcmp(argv[2], "--manual-request");
    if (!((argc == 2 && !strcmp(argv[1], "--isolated-fixture")) || manual)) return 77;
    if (!isolated()) { fputs("Requires the isolated test runner\n", stderr); return 77; }
    /* All ancestors are created once by the trusted isolated harness. Pin the
     * allowed directory before accepting requests; no caller-supplied paths. */
    int rootfd = open("/tmp/symlink-fixture/allowed",
                      O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (rootfd < 0) { perror("fixture directory"); return 77; }
    if (manual) {
        int status = handle_manual_request(rootfd, argv[3]);
        close(rootfd);
        return status;
    }
    struct sockaddr_un address = {.sun_family = AF_UNIX};
    memcpy(address.sun_path, "/run/symlink.sock", sizeof("/run/symlink.sock"));
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
