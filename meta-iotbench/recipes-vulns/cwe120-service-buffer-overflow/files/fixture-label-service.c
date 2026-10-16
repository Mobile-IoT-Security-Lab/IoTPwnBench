#define _POSIX_C_SOURCE 200809L
/* INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT */
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/un.h>
#include <unistd.h>

#define MAX_FIELD 1024
#define DEFAULT_SOCKET "/run/iotbench-label/service.sock"

static int receive_exact(int fd, unsigned char *data, size_t size)
{
    size_t offset = 0;
    while (offset < size) {
        ssize_t count = recv(fd, data + offset, size - offset, 0);
        if (count < 0 && errno == EINTR)
            continue;
        if (count <= 0)
            return -1;
        offset += (size_t)count;
    }
    return 0;
}

static int handle_label_request(const char *field)
{
    char label[32];
    /* CWE-120 / CWE-121: no validation that strlen(field) < sizeof(label). */
    strcpy(label, field);
    /* A harmless in-memory label operation; no persistent state or commands. */
    return label[0] != '\0';
}

static int serve_request(int fd)
{
    unsigned char header[2], extra;
    char field[MAX_FIELD + 1];
    size_t length;
    ssize_t tail;
    static const char response[] = "SYNTHETIC_LABEL_UPDATED\n";

    if (receive_exact(fd, header, sizeof(header)) != 0)
        return 2;
    length = (size_t)header[0] * 256 + header[1];
    if (length == 0 || length > MAX_FIELD)
        return 2;
    if (receive_exact(fd, (unsigned char *)field, length) != 0)
        return 2;
    do {
        tail = recv(fd, &extra, 1, 0);
    } while (tail < 0 && errno == EINTR);
    if (tail != 0) /* Client must half-close: reject trailing or incomplete frames. */
        return 2;
    for (size_t i = 0; i < length; ++i) {
        if ((unsigned char)field[i] < 0x20 || (unsigned char)field[i] > 0x7e)
            return 2;
    }
    field[length] = '\0';
    if (!handle_label_request(field))
        return 2;
    for (size_t offset = 0; offset < sizeof(response) - 1;) {
        ssize_t count = send(fd, response + offset, sizeof(response) - 1 - offset, 0);
        if (count < 0 && errno == EINTR)
            continue;
        if (count <= 0)
            return 2;
        offset += (size_t)count;
    }
    return 0;
}

int main(int argc, char **argv)
{
    const char *path = DEFAULT_SOCKET;
    struct sockaddr_un address = {0};
    struct timeval timeout = {3, 0};
    struct rlimit no_core = {0, 0};
    int listener, client, result;

    fputs("INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT\n", stderr);
    if (argc == 3 && strcmp(argv[1], "--socket") == 0)
        path = argv[2];
    else if (argc != 1)
        return 2;
    if (path[0] != '/' || strlen(path) >= sizeof(address.sun_path))
        return 2;
    if (setrlimit(RLIMIT_CORE, &no_core) != 0 || signal(SIGPIPE, SIG_IGN) == SIG_ERR)
        return 2;
    umask(0077);
    address.sun_family = AF_UNIX;
    memcpy(address.sun_path, path, strlen(path) + 1);
    listener = socket(AF_UNIX, SOCK_STREAM, 0);
    if (listener < 0)
        return 2;
    /* Never remove a pre-existing path. Use a private runtime directory. */
    if (bind(listener, (struct sockaddr *)&address, sizeof(address)) != 0) {
        close(listener);
        return 2;
    }
    if (listen(listener, 1) != 0) {
        close(listener);
        unlink(path);
        return 2;
    }
    do {
        client = accept(listener, NULL, NULL);
    } while (client < 0 && errno == EINTR);
    result = 2;
    if (client >= 0) {
        if (setsockopt(client, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) == 0 &&
            setsockopt(client, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout)) == 0)
            result = serve_request(client);
        close(client);
    }
    close(listener);
    unlink(path);
    return result;
}
