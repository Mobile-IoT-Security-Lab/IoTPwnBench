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
            char command[320];
            snprintf(command, sizeof(command), "printf 'service status for %%s\\n' %s", input);
            FILE *fp = popen(command, "r");
            if (fp != NULL) {
                char out[256];
                while (fgets(out, sizeof(out), fp) != NULL) {
                    write(client, out, strlen(out));
                }
                pclose(fp);
            }
        }
        close(client);
        while (waitpid(-1, NULL, WNOHANG) > 0) {}
    }
}
