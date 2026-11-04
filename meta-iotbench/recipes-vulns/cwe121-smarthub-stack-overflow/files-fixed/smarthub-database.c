/* SmartThings-style database lookup CGI, corrected variant of CWE-121. */
#include <ctype.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct request_frame {
    char bucket[64];
    volatile uint32_t authorization;
    /* Padding kept so that the layout equals the one of the vulnerable image. */
    char guard[32];
};

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
    const char *value = query ? strstr(query, "bucket=") : NULL;
    char decoded[160] = "devices";
    struct request_frame frame;

    memset(&frame, 0, sizeof(frame));
    if (value) {
        value += 7;
        url_decode(decoded, sizeof(decoded), value);
        char *amp = strchr(decoded, '&');
        if (amp) *amp = '\0';
    }

    /* The input is truncated to the size of the bucket field. */
    memcpy(frame.bucket, decoded, strnlen(decoded, sizeof(frame.bucket) - 1));

    printf("Content-Type: text/plain\r\n\r\n");
    if (memcmp((const void *)&frame.authorization, "ROOT", 4) == 0)
        printf("STACK_OVERFLOW authorization=admin\n");
    else
        printf("bucket=%s authorization=user\n", frame.bucket);
    return 0;
}
