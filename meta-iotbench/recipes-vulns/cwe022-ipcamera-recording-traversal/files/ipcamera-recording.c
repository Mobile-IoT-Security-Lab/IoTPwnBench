/* Intentionally vulnerable recording export CGI for the IoTBench IP camera. */
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

    /* CWE-22: traversal components are appended without canonicalization. */
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
