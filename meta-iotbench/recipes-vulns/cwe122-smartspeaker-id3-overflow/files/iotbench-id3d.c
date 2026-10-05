/* Intentionally vulnerable ID3 title parser for the IoTBench smart speaker. */
#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define PORT 18000

struct media_metadata {
    unsigned char title[64];
    unsigned char decoder_state[4];
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
    unsigned char header[4];
    unsigned char title[68];
    if (receive_exact(client, header, sizeof(header)) < 0 ||
        memcmp(header, "ID3", 3) != 0) {
        send(client, "INVALID_ID3\n", 12, 0);
        return;
    }
    size_t length = header[3];
    if (length == 0 || length > sizeof(title) ||
        receive_exact(client, title, length) < 0) {
        send(client, "INVALID_ID3\n", 12, 0);
        return;
    }

    struct media_metadata *metadata = malloc(sizeof(*metadata));
    if (!metadata) return;
    memset(metadata, 0, sizeof(*metadata));
    memcpy(metadata->decoder_state, "SAFE", 4);

    /* CWE-122: the ID3 length is trusted for a smaller heap title field. */
    memcpy(metadata->title, title, length);

    if (memcmp(metadata->decoder_state, "SAFE", 4) != 0)
        send(client, "HEAP_OVERFLOW decoder-state-corrupted\n", 38, 0);
    else
        send(client, "TRACK_INDEXED\n", 14, 0);
    free(metadata);
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
