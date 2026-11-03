/* Recording export CGI for the IoTBench IP camera, corrected variant of CWE-22. */
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void url_decode(char *dst, size_t cap, const char *src)
{
    size_t out = 0;
    while (*src && out + 1 < cap) {
        if (src[0] == '%' && isxdigit((unsigned char)src[1]) &&
            isxdigit((unsigned char)src[2])) {
            char hex[3] = { src[1], src[2], '\0' };
            dst[out++] = (char)strtoul(hex, NULL, 16);
            src += 3;
        } else {
            dst[out++] = *src == '+' ? ' ' : *src;
            src++;
        }
    }
    dst[out] = '\0';
}

int main(void)
{
    const char *query = getenv("QUERY_STRING");
    const char *value = query ? strstr(query, "file=") : NULL;
    char requested[256] = "clip-001.txt";
    char path[512];

    if (value) {
        value += 5;
        url_decode(requested, sizeof(requested), value);
        char *amp = strchr(requested, '&');
        if (amp) *amp = '\0';
    }

    /* A recording is a plain file name, so path separators and parent references are rejected. */
    if (strchr(requested, '/') || strstr(requested, "..")) {
        printf("Status: 400 Bad Request\r\nContent-Type: text/plain\r\n\r\ninvalid recording name\n");
        return 0;
    }
    snprintf(path, sizeof(path), "/var/lib/ipcamera/recordings/%s", requested);
    FILE *input = fopen(path, "rb");
    if (!input) {
        printf("Status: 404 Not Found\r\nContent-Type: text/plain\r\n\r\nrecording not found\n");
        return 0;
    }

    printf("Content-Type: application/octet-stream\r\n\r\n");
    char buffer[512];
    size_t count;
    while ((count = fread(buffer, 1, sizeof(buffer), input)) > 0)
        fwrite(buffer, 1, count, stdout);
    fclose(input);
    return 0;
}
