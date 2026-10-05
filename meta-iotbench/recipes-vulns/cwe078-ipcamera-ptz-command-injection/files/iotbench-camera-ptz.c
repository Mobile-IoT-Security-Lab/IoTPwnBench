/*
 * INTENTIONALLY VULNERABLE CGI for the isolated IoTBench lab.
 * Models an embedded camera PTZ handler that sends an HTTP parameter to a
 * vendor shell utility without neutralizing command separators (CWE-78).
 */
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int hex_value(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    c = (char)tolower((unsigned char)c);
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    return -1;
}

static void url_decode(char *value)
{
    char *src = value;
    char *dst = value;

    while (*src) {
        if (*src == '%' && src[1] && src[2]) {
            int hi = hex_value(src[1]);
            int lo = hex_value(src[2]);
            if (hi >= 0 && lo >= 0) {
                *dst++ = (char)((hi << 4) | lo);
                src += 3;
                continue;
            }
        }
        *dst++ = (*src == '+') ? ' ' : *src;
        src++;
    }
    *dst = '\0';
}

int main(void)
{
    const char *query = getenv("QUERY_STRING");
    char preset[241];
    char command[512];
    char output[256];

    printf("Content-Type: text/plain; charset=utf-8\r\n\r\n");
    if (!query || strncmp(query, "preset=", 7) != 0) {
        puts("usage: /cgi-bin/ptz.cgi?preset=home");
        return 0;
    }

    snprintf(preset, sizeof(preset), "%s", query + 7);
    char *amp = strchr(preset, '&');
    if (amp) *amp = '\0';
    url_decode(preset);

    /* CWE-78: preset is interpreted by /bin/sh as part of the command. */
    if (snprintf(command, sizeof(command),
                 "echo PTZ-preset-applied: %s", preset) >= (int)sizeof(command)) {
        puts("preset too long");
        return 0;
    }

    FILE *pipe = popen(command, "r");
    if (!pipe) {
        puts("PTZ helper failed");
        return 0;
    }
    while (fgets(output, sizeof(output), pipe)) fputs(output, stdout);
    pclose(pipe);
    return 0;
}
