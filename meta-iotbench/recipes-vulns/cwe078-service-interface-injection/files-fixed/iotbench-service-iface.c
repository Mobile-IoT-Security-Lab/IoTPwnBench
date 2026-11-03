#include <ctype.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void) {
    int server = socket(AF_INET, SOCK_STREAM, 0);
    int one = 1;
    setsockopt(server, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(9090);
    if (bind(server, (struct sockaddr *)&addr, sizeof(addr)) != 0 || listen(server, 8) != 0) {
        perror("service-iface");
        return 1;
    }
    for (;;) {
        int client = accept(server, NULL, NULL);
        if (client < 0) {
            continue;
        }
        char input[192] = {0};
        ssize_t n = read(client, input, sizeof(input) - 1);
        if (n > 0) {
            input[strcspn(input, "\r\n")] = '\0';
            /* The request is a service name made of letters, digits, dots, hyphens and underscores. */
            int valid = input[0] != '\0';
            for (const char *c = input; *c; ++c) {
                if (!isalnum((unsigned char)*c) && *c != '.' && *c != '-' && *c != '_') valid = 0;
            }
            char out[256];
            if (valid) snprintf(out, sizeof(out), "service status for %s\n", input);
            else snprintf(out, sizeof(out), "invalid service name\n");
            write(client, out, strlen(out));
        }
        close(client);
        while (waitpid(-1, NULL, WNOHANG) > 0) {}
    }
}
