/* Vendor-specific Modbus project loader, corrected variant of CWE-121. */
#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define PORT 502

struct project_chunk {
    unsigned char data[32];
    unsigned char safety_state[4];
};

static volatile sig_atomic_t running = 1;
static void stop_server(int sig) { (void)sig; running = 0; }

static uint16_t read_u16(const unsigned char *p)
{
    return (uint16_t)(((uint16_t)p[0] << 8) | p[1]);
}

static void write_u16(unsigned char *p, uint16_t value)
{
    p[0] = (unsigned char)(value >> 8);
    p[1] = (unsigned char)value;
}

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

static void reply_status(int client, const unsigned char *request, unsigned char status)
{
    unsigned char response[9];
    memcpy(response, request, 4);
    write_u16(response + 4, 3);
    response[6] = request[6];
    response[7] = 0x41;
    response[8] = status;
    send(client, response, sizeof(response), 0);
}

static void serve(int client)
{
    unsigned char request[260];
    while (running) {
        if (receive_exact(client, request, 7) < 0) return;
        uint16_t mbap_length = read_u16(request + 4);
        if (mbap_length < 3 || mbap_length > sizeof(request) - 6) return;
        size_t remaining = (size_t)mbap_length - 1;
        if (receive_exact(client, request + 7, remaining) < 0) return;
        if (request[7] != 0x41) {
            reply_status(client, request, 0x02);
            continue;
        }

        size_t chunk_length = request[8];
        if (chunk_length == 0 || chunk_length > sizeof(((struct project_chunk *)0)->data) || remaining < 2 + chunk_length) {
            reply_status(client, request, 0x03);
            continue;
        }

        struct project_chunk frame;
        memset(&frame, 0, sizeof(frame));
        memcpy(frame.safety_state, "SAFE", 4);

        /* The chunk length was checked against the size of the field above. */
        memcpy(frame.data, request + 9, chunk_length);
        reply_status(client, request,
                     memcmp(frame.safety_state, "SAFE", 4) == 0 ? 0x00 : 0x01);
    }
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
