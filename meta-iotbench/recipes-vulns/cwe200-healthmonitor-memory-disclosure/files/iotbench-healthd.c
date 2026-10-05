/* Intentionally unauthenticated patient-monitor memory read service. */
#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define PORT 2575

static volatile sig_atomic_t running = 1;
static void stop_server(int sig) { (void)sig; running = 0; }

static void serve(int client)
{
    char request[128];
    unsigned char device_memory[256];
    memset(device_memory, '.', sizeof(device_memory));
    static const char patient[] =
        "patient_id=PT-1042;name=Alice Example;spo2=97;hr=72;";
    static const char secrets[] =
        "wifi_psk=clinical-monitor-lab;alarm_pin=1842;";
    memcpy(device_memory + 32, patient, sizeof(patient) - 1);
    memcpy(device_memory + 128, secrets, sizeof(secrets) - 1);

    ssize_t count = recv(client, request, sizeof(request) - 1, 0);
    if (count <= 0) return;
    request[count] = '\0';
    unsigned offset = 0, length = 0;
    if (sscanf(request, "READ %u %u", &offset, &length) != 2 ||
        length == 0 || offset >= sizeof(device_memory) ||
        length > sizeof(device_memory) - offset) {
        send(client, "usage: READ <offset> <length>\n", 30, 0);
        return;
    }

    /* CWE-200: sensitive memory is returned without authenticating the peer. */
    send(client, device_memory + offset, length, 0);
    send(client, "\n", 1, 0);
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
