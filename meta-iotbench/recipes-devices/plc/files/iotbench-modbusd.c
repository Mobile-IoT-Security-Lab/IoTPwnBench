/*
 * iotbench-modbusd - minimal Modbus/TCP server for the PLC device skeleton.
 *
 * Exposes the simulated peripheral values (from /run/iotbench/state.env) as
 * Modbus holding and input registers, each scaled x100 and clamped to uint16.
 * Numeric peripherals map to registers 0..N-1 in file order; string (enum)
 * values are skipped. Serves one client at a time on TCP port 502.
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <modbus.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <unistd.h>

#define MAXREG 32

static volatile sig_atomic_t running = 1;
static void on_signal(int s) { (void)s; running = 0; }

static int load_values(const char *path, uint16_t *regs, int maxn)
{
    FILE *f = fopen(path, "r");
    if (!f) return 0;
    char line[256];
    int n = 0;
    while (fgets(line, sizeof(line), f) && n < maxn) {
        char *eq = strchr(line, '=');
        if (!eq) continue;
        *eq = '\0';
        if (!strcmp(line, "TS")) continue;
        char *end;
        double d = strtod(eq + 1, &end);
        if (end == eq + 1) continue; /* non-numeric (enum) -> skip */
        long scaled = (long)(d * 100.0);
        if (scaled < 0) scaled = 0;
        if (scaled > 65535) scaled = 65535;
        regs[n++] = (uint16_t)scaled;
    }
    fclose(f);
    return n;
}

int main(int argc, char **argv)
{
    const char *env_file = "/run/iotbench/state.env";
    int port = 502;
    if (argc > 1) port = atoi(argv[1]);

    signal(SIGTERM, on_signal);
    signal(SIGINT, on_signal);

    modbus_t *ctx = modbus_new_tcp("0.0.0.0", port);
    if (!ctx) { fprintf(stderr, "modbus_new_tcp failed\n"); return 1; }
    modbus_mapping_t *mb = modbus_mapping_new(0, 0, MAXREG, MAXREG);
    if (!mb) { modbus_free(ctx); return 1; }

    int server = modbus_tcp_listen(ctx, 1);
    if (server == -1) {
        fprintf(stderr, "listen failed: %s\n", modbus_strerror(errno));
        modbus_mapping_free(mb);
        modbus_free(ctx);
        return 1;
    }

    int client = -1;
    uint8_t query[MODBUS_TCP_MAX_ADU_LENGTH];

    while (running) {
        /* Refresh registers from the simulator each loop. */
        load_values(env_file, mb->tab_registers, MAXREG);
        memcpy(mb->tab_input_registers, mb->tab_registers, MAXREG * sizeof(uint16_t));

        fd_set rfds;
        FD_ZERO(&rfds);
        FD_SET(server, &rfds);
        int maxfd = server;
        if (client != -1) {
            FD_SET(client, &rfds);
            if (client > maxfd) maxfd = client;
        }
        struct timeval tv = { 2, 0 };
        int r = select(maxfd + 1, &rfds, NULL, NULL, &tv);
        if (r < 0) { if (errno == EINTR) continue; break; }
        if (r == 0) continue; /* timeout: refresh registers */

        if (FD_ISSET(server, &rfds)) {
            int c = modbus_tcp_accept(ctx, &server);
            if (c != -1) {
                if (client != -1) close(client);
                client = c;
            }
        }
        if (client != -1 && FD_ISSET(client, &rfds)) {
            modbus_set_socket(ctx, client);
            int rc = modbus_receive(ctx, query);
            if (rc > 0) modbus_reply(ctx, query, rc, mb);
            else if (rc == -1) { close(client); client = -1; }
        }
    }

    if (client != -1) close(client);
    close(server);
    modbus_mapping_free(mb);
    modbus_free(ctx);
    return 0;
}
