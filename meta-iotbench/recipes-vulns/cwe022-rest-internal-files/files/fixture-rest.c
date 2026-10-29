/* Synthetic CWE-22/CWE-73 benchmark; see NOTICE and ground-truth.json. */
#define _GNU_SOURCE
#include <stdio.h>
#ifndef IOTBENCH_REST_FIXTURE_ENABLED
#define IOTBENCH_REST_FIXTURE_ENABLED 0
#endif
#if !IOTBENCH_REST_FIXTURE_ENABLED
int main(void) { fputs("REST fixture disabled in production\n", stderr); return 77; }
#else
#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/openat2.h>
#include <signal.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/time.h>
#include <sys/un.h>
#include <unistd.h>
/* Older libc syscall aliases may lag behind the target kernel UAPI. */
#ifndef SYS_openat2
#define SYS_openat2 __NR_openat2
#endif
#ifndef FIXTURE_BASE
#error "The dedicated fixture base must be supplied by the test build"
#endif
#ifndef REST_SECURE_CONTROL
#define REST_SECURE_CONTROL 0
#endif
#define REQUEST_MAX 4096
#define FILE_MAX 4096
#define NAME_MAXIMUM 255
static const char manifest[] = "IOTBENCH_REST_TEST_ONLY_V1\nmode=fixture\nenabled=1\n";

/* The outer research boundary is enforced atomically by the kernel, including
 * symlink/mount races. It intentionally permits fs/api -> fs/restricted. */
static int confined_open(int rootfd, const char *path, int directory)
{
    struct open_how how = {
        .flags = O_RDONLY | O_CLOEXEC | O_NOCTTY | O_NONBLOCK,
        .resolve = RESOLVE_BENEATH | RESOLVE_NO_SYMLINKS | RESOLVE_NO_XDEV
    };
    if (directory) how.flags |= O_DIRECTORY;
    return (int)syscall(SYS_openat2, rootfd, path, &how, sizeof(how));
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

static void respond(int fd, int status, const char *body, size_t size)
{
    char header[256];
    const char *reason = status == 200 ? "OK" : status == 400 ? "Bad Request" :
        status == 403 ? "Forbidden" : status == 404 ? "Not Found" :
        status == 405 ? "Method Not Allowed" : "Request Too Large";
    int n = snprintf(header, sizeof(header),
        "HTTP/1.1 %d %s\r\nContent-Length: %zu\r\nContent-Type: text/plain\r\n"
        "Connection: close\r\n\r\n", status, reason, size);
    if (n > 0 && (size_t)n < sizeof(header) && !send_all(fd, header, (size_t)n))
        (void)send_all(fd, body, size);
}

static int hex_digit(unsigned char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

/* Exactly one form parameter, decoded once, with bounded, printable path data.
 * This is syntax checking, deliberately NOT directory validation. */
static int extract_file_parameter(const char *form, char *file)
{
    size_t out = 0;
    if (strncmp(form, "file=", 5)) return -1;
    for (size_t i = 5; form[i]; ++i) {
        unsigned char c = (unsigned char)form[i];
        if (c == '%') {
            if (!form[i + 1] || !form[i + 2]) return -1;
            int a = hex_digit((unsigned char)form[i + 1]);
            int b = hex_digit((unsigned char)form[i + 2]);
            if (a < 0 || b < 0) return -1;
            c = (unsigned char)((a << 4) | b);
            i += 2;
        }
        if (!(isalnum(c) || c == '_' || c == '-' || c == '.' || c == '/') ||
            out == NAME_MAXIMUM) return -1;
        file[out++] = (char)c;
    }
    file[out] = '\0';
    return out ? 0 : -1;
}

static int safe_basename(const char *file)
{
    if (!strcmp(file, ".") || !strcmp(file, "..")) return 0;
    for (size_t i = 0; file[i]; ++i)
        if (!(isalnum((unsigned char)file[i]) || file[i] == '_' ||
              file[i] == '-' || file[i] == '.')) return 0;
    return *file != '\0';
}

static int read_internal_file(int rootfd, const char *file, int vulnerable,
                              char *body, size_t *size)
{
    char path[sizeof("api/") + NAME_MAXIMUM];
    struct stat st;
    if (!vulnerable && !safe_basename(file)) return 403;
    /* INTENTIONAL CWE-22/CWE-73: the vulnerable config route fails to enforce
     * the api directory boundary before passing HTTP input to a file open. */
    int length = snprintf(path, sizeof(path), "api/%s", file);
    if (length < 0 || (size_t)length >= sizeof(path)) return 400;
    int input = confined_open(rootfd, path, 0); /* read-only filesystem sink */
    int open_error = errno;
    fprintf(stderr, "fixture-read path=%s result=%s\n", path,
            input < 0 ? "blocked-or-missing" : "opened");
    if (input < 0) return open_error == ENOENT ? 404 : 403;
    if (fstat(input, &st) || !S_ISREG(st.st_mode) || st.st_size > FILE_MAX) {
        close(input);
        return 403;
    }
    *size = 0;
    while (*size < FILE_MAX) {
        ssize_t n = read(input, body + *size, FILE_MAX - *size);
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) { close(input); return 403; }
        if (!n) break;
        *size += (size_t)n;
    }
    close(input);
    return 200;
}

static int receive_more(int fd, char *request, size_t *used)
{
    if (*used == REQUEST_MAX) return -1;
    ssize_t n;
    do { n = recv(fd, request + *used, REQUEST_MAX - *used, 0); }
    while (n < 0 && errno == EINTR);
    if (n <= 0) return -1;
    /* Embedded NUL and non-HTTP control characters never reach string parsing. */
    for (ssize_t i = 0; i < n; ++i) {
        unsigned char c = (unsigned char)request[*used + (size_t)i];
        if ((c < 32 && c != '\r' && c != '\n' && c != '\t') || c > 126) return -1;
    }
    *used += (size_t)n;
    request[*used] = '\0';
    return 0;
}

static void handle_http_request(int client, int rootfd)
{
    char request[REQUEST_MAX + 1] = {0}, body[FILE_MAX], file[NAME_MAXIMUM + 1];
    size_t used = 0, size = 0, content_length = 0;
    char *end;
    while (!(end = strstr(request, "\r\n\r\n")))
        if (receive_more(client, request, &used)) goto malformed;
    size_t header_size = (size_t)(end - request) + 4;
    char *line = strstr(request, "\r\n");
    if (!line) goto malformed;
    *line = '\0';
    char *target = strchr(request, ' ');
    if (!target) goto malformed;
    *target++ = '\0';
    char *version = strchr(target, ' ');
    if (!version) goto malformed;
    *version++ = '\0';
    if (strcmp(version, "HTTP/1.1") && strcmp(version, "HTTP/1.0")) goto malformed;
    int have_length = 0, have_type = 0;
    for (char *header = line + 2; header < end; header = line + 2) {
        line = strstr(header, "\r\n");
        if (!line || line > end) goto malformed;
        *line = '\0';
        char *value = strchr(header, ':');
        if (!value || value == header) goto malformed;
        *value++ = '\0';
        for (char *p = header; *p; ++p)
            if (!(isalnum((unsigned char)*p) || *p == '-')) goto malformed;
        while (*value == ' ' || *value == '\t') ++value;
        for (char *p = value; *p; ++p)
            if ((unsigned char)*p < 32 || (unsigned char)*p > 126) goto malformed;
        if (!strcasecmp(header, "Transfer-Encoding")) goto malformed;
        if (!strcasecmp(header, "Content-Length")) {
            if (have_length++ || !*value) goto malformed;
            for (char *p = value; *p; ++p) {
                if (!isdigit((unsigned char)*p) || content_length > REQUEST_MAX / 10)
                    goto malformed;
                content_length = content_length * 10 + (size_t)(*p - '0');
            }
        }
        if (!strcasecmp(header, "Content-Type")) {
            if (have_type++ || strcmp(value, "application/x-www-form-urlencoded"))
                goto malformed;
        }
    }
    if (content_length > 512 || header_size + content_length > REQUEST_MAX) goto malformed;
    while (used < header_size + content_length)
        if (receive_more(client, request, &used)) goto malformed;
    if (used != header_size + content_length) goto malformed;
    int is_get = !strcmp(request, "GET"), is_post = !strcmp(request, "POST");
    if (!is_get && !is_post) { respond(client, 405, "method unavailable\n", 19); return; }
    char *form = strchr(target, '?');
    if (form) *form++ = '\0';
    int vulnerable = 0;
    if (is_get && (!strcmp(target, "/api/config") || !strcmp(target, "/api/status"))) {
        if (content_length || !form) goto malformed;
        vulnerable = !REST_SECURE_CONTROL && !strcmp(target, "/api/config");
    } else if (is_post && !strcmp(target, "/api/config/read")) {
        if (form || !have_length || !have_type) goto malformed;
        form = request + header_size;
    } else { respond(client, 404, "route unavailable\n", 18); return; }
    if (extract_file_parameter(form, file)) goto malformed; /* HTTP source */
    int status = read_internal_file(rootfd, file, vulnerable, body, &size);
    if (status == 200) respond(client, status, body, size);
    else respond(client, status, "file unavailable\n", 17);
    return;
malformed:
    respond(client, 400, "invalid request\n", 16);
}

int main(int argc, char **argv)
{
    if (argc != 2 || strcmp(argv[1], "--isolated-fixture")) return 77;
    if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)) return 77;
    int rootfd = open(FIXTURE_BASE "/fs", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (rootfd < 0) { perror("fixture fs"); return 77; }
    int marker = confined_open(rootfd, ".fixture-test-only", 0);
    char check[sizeof(manifest)] = {0};
    struct stat st;
    if (marker < 0 || fstat(marker, &st) || !S_ISREG(st.st_mode) ||
        (st.st_mode & 0777) != 0644 || st.st_size != sizeof(manifest) - 1 ||
        read(marker, check, sizeof(check)) != (ssize_t)sizeof(manifest) - 1 ||
        memcmp(check, manifest, sizeof(manifest) - 1)) {
        fputs("Fixture manifest or kernel openat2 confinement unavailable\n", stderr);
        if (marker >= 0) close(marker);
        close(rootfd);
        return 77;
    }
    close(marker); /* Also probes openat2 support; never fall back to open(). */
    struct sockaddr_un address = {.sun_family = AF_UNIX};
    const char *socket_path = FIXTURE_BASE "/run/rest.sock";
    if (strlen(socket_path) >= sizeof(address.sun_path)) { close(rootfd); return 77; }
    memcpy(address.sun_path, socket_path, strlen(socket_path) + 1);
    umask(0077);
    int listener = socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
    /* Refuse existing socket paths; the test runner owns their cleanup. */
    if (listener < 0 || bind(listener, (struct sockaddr *)&address, sizeof(address)) ||
        listen(listener, 8)) {
        perror("fixture Unix socket");
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
            handle_http_request(client, rootfd);
        close(client); /* Exactly one request per connection, no keepalive. */
    }
    close(listener);
    close(rootfd);
    return 0;
}
#endif
