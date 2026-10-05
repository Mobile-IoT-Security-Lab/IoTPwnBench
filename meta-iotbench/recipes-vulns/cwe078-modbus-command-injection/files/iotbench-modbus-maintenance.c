/*
 * INTENTIONALLY VULNERABLE Modbus/TCP maintenance service for IoTBench.
 * Holding registers 100..131 stage a project name, register 132 applies it,
 * and registers 140..203 expose the command output. The apply operation sends
 * the untrusted project name to /bin/sh (CWE-78).
 */
#define _POSIX_C_SOURCE 200809L
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

#define MODBUS_PORT 502
#define REGISTER_COUNT 256
#define PROJECT_START 100
#define PROJECT_REGS 32
#define APPLY_REGISTER 132
#define RESULT_START 140
#define RESULT_REGS 64

static uint16_t registers[REGISTER_COUNT];
static volatile sig_atomic_t running = 1;

static void stop_server(int sig)
{
    (void)sig;
    running = 0;
}

static uint16_t read_u16(const uint8_t *p)
{
    return (uint16_t)(((uint16_t)p[0] << 8) | p[1]);
}

static void write_u16(uint8_t *p, uint16_t value)
{
    p[0] = (uint8_t)(value >> 8);
    p[1] = (uint8_t)(value & 0xff);
}

static ssize_t recv_exact(int fd, void *buffer, size_t size)
{
    size_t received = 0;
    while (received < size) {
        ssize_t n = recv(fd, (char *)buffer + received, size - received, 0);
        if (n == 0) return 0;
        if (n < 0) {
            if (errno == EINTR) continue;
            return -1;
        }
        received += (size_t)n;
    }
    return (ssize_t)received;
}

static int send_all(int fd, const uint8_t *buffer, size_t size)
{
    size_t sent = 0;
    while (sent < size) {
        ssize_t n = send(fd, buffer + sent, size - sent, 0);
        if (n < 0) {
            if (errno == EINTR) continue;
            return -1;
        }
        sent += (size_t)n;
    }
    return 0;
}

static void store_result(const char *text)
{
    size_t length = strlen(text);
    memset(&registers[RESULT_START], 0, RESULT_REGS * sizeof(uint16_t));
    if (length > RESULT_REGS * 2 - 1) length = RESULT_REGS * 2 - 1;
    for (size_t i = 0; i < length; i++) {
        if ((i & 1U) == 0)
            registers[RESULT_START + i / 2] = (uint16_t)((uint8_t)text[i] << 8);
        else
            registers[RESULT_START + i / 2] |= (uint8_t)text[i];
    }
}

static void apply_project(void)
{
    char project[PROJECT_REGS * 2 + 1];
    char command[256];
    char result[RESULT_REGS * 2];
    size_t pos = 0;

    for (int i = 0; i < PROJECT_REGS && pos + 1 < sizeof(project); i++) {
        char high = (char)(registers[PROJECT_START + i] >> 8);
        char low = (char)(registers[PROJECT_START + i] & 0xff);
        if (!high) break;
        project[pos++] = high;
        if (!low) break;
        project[pos++] = low;
    }
    project[pos] = '\0';

    /* CWE-78: the project field reaches the shell without neutralization. */
    snprintf(command, sizeof(command), "echo PLC-project-applied: %s", project);
    FILE *pipe = popen(command, "r");
    if (!pipe) {
        store_result("project helper failed\n");
        return;
    }

    size_t used = 0;
    while (used + 1 < sizeof(result)) {
        size_t n = fread(result + used, 1, sizeof(result) - used - 1, pipe);
        used += n;
        if (n == 0) break;
    }
    result[used] = '\0';
    pclose(pipe);
    store_result(result);
}

static size_t exception_response(const uint8_t *request, uint8_t *response,
                                 uint8_t function, uint8_t code)
{
    memcpy(response, request, 4);
    write_u16(response + 4, 3);
    response[6] = request[6];
    response[7] = (uint8_t)(function | 0x80);
    response[8] = code;
    return 9;
}

static size_t handle_request(const uint8_t *request, size_t request_size,
                             uint8_t *response)
{
    uint8_t function = request[7];
    if (request_size < 12)
        return exception_response(request, response, function, 3);

    uint16_t address = read_u16(request + 8);
    uint16_t count = read_u16(request + 10);

    if (function == 3) {
        if (count == 0 || count > 125 || address + count > REGISTER_COUNT)
            return exception_response(request, response, function, 2);
        memcpy(response, request, 4);
        write_u16(response + 4, (uint16_t)(3 + count * 2));
        response[6] = request[6];
        response[7] = function;
        response[8] = (uint8_t)(count * 2);
        for (uint16_t i = 0; i < count; i++)
            write_u16(response + 9 + i * 2, registers[address + i]);
        return (size_t)(9 + count * 2);
    }

    if (function == 6) {
        if (address >= REGISTER_COUNT)
            return exception_response(request, response, function, 2);
        registers[address] = count;
        if (address == APPLY_REGISTER && count == 1) {
            apply_project();
            registers[APPLY_REGISTER] = 0;
        }
        memcpy(response, request, 12);
        return 12;
    }

    if (function == 16) {
        if (request_size < 13 || count == 0 || count > 123 ||
            address + count > REGISTER_COUNT || request[12] != count * 2 ||
            request_size < (size_t)(13 + count * 2))
            return exception_response(request, response, function, 3);
        for (uint16_t i = 0; i < count; i++)
            registers[address + i] = read_u16(request + 13 + i * 2);
        memcpy(response, request, 12);
        write_u16(response + 4, 6);
        return 12;
    }

    return exception_response(request, response, function, 1);
}

static void serve_client(int client)
{
    uint8_t request[260];
    uint8_t response[260];

    while (running) {
        ssize_t n = recv_exact(client, request, 7);
        if (n <= 0) return;
        uint16_t mbap_length = read_u16(request + 4);
        if (mbap_length < 2 || mbap_length > sizeof(request) - 6) return;
        size_t remaining = (size_t)mbap_length - 1;
        n = recv_exact(client, request + 7, remaining);
        if (n <= 0) return;
        size_t response_size = handle_request(request, 7 + remaining, response);
        if (send_all(client, response, response_size) < 0) return;
    }
}

int main(void)
{
    signal(SIGTERM, stop_server);
    signal(SIGINT, stop_server);

    int server = socket(AF_INET, SOCK_STREAM, 0);
    if (server < 0) return 1;
    int reuse = 1;
    setsockopt(server, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));

    struct sockaddr_in address = {
        .sin_family = AF_INET,
        .sin_port = htons(MODBUS_PORT),
        .sin_addr.s_addr = htonl(INADDR_ANY),
    };
    if (bind(server, (struct sockaddr *)&address, sizeof(address)) < 0 ||
        listen(server, 4) < 0) {
        perror("modbus maintenance listen");
        close(server);
        return 1;
    }

    while (running) {
        int client = accept(server, NULL, NULL);
        if (client < 0) {
            if (errno == EINTR) continue;
            break;
        }
        serve_client(client);
        close(client);
    }
    close(server);
    return 0;
}
