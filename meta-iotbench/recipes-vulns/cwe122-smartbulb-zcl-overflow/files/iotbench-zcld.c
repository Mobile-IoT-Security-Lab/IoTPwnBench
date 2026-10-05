/* Intentionally vulnerable ZCL commissioning parser for IoTBench. */
#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define PORT 17754

struct zcl_attribute {
    unsigned char value[32];
    unsigned char integrity[4];
};

static volatile sig_atomic_t running = 1;
static void stop_server(int sig) { (void)sig; running = 0; }

static int receive_exact(int fd, void *buffer, size_t length)
{
    size_t used = 0;
    while (used < length) {
        ssize_t count = recv(fd, (char *)buffer + used, length - used, 0);
        if (count <= 0) return -1;
        used += (size_t)count;
    }
    return 0;
}

static void serve(int client)
{
    unsigned char header[2];
    unsigned char input[36];
    if (receive_exact(client, header, sizeof(header)) < 0) return;
    size_t length = (size_t)(((unsigned)header[0] << 8) | header[1]);
    if (length == 0 || length > sizeof(input) ||
        receive_exact(client, input, length) < 0) {
        send(client, "INVALID_FRAME\n", 14, 0);
        return;
    }

    struct zcl_attribute *attribute = malloc(sizeof(*attribute));
    if (!attribute) return;
    memset(attribute, 0, sizeof(*attribute));
    memcpy(attribute->integrity, "SAFE", 4);

    /* CWE-122: protocol length permits 36 bytes, heap field holds only 32. */
    memcpy(attribute->value, input, length);

    if (memcmp(attribute->integrity, "SAFE", 4) != 0)
        send(client, "HEAP_OVERFLOW zcl-integrity-corrupted\n", 38, 0);
    else
        send(client, "COMMISSIONED\n", 13, 0);
    free(attribute);
}

int main(void)
{
    signal(SIGTERM, stop_server);
    signal(SIGINT, stop_server);
    int server = socket(AF_INET, SOCK_STREAM, 0);
    int reuse = 1;
    setsockopt(server, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));
    struct sockaddr_in address = { .sin_family = AF_INET,
        .sin_port = htons(PORT), .sin_addr.s_addr = htonl(INADDR_ANY) };
    if (server < 0 || bind(server, (struct sockaddr *)&address, sizeof(address)) < 0 ||
        listen(server, 4) < 0) return 1;
    while (running) {
        int client = accept(server, NULL, NULL);
        if (client < 0) { if (errno == EINTR) continue; break; }
        serve(client);
        close(client);
    }
    close(server);
    return 0;
}
