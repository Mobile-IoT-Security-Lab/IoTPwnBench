/* Intentionally vulnerable SmartThings-style database lookup CGI. */
#include <ctype.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct request_frame {
    char bucket[64];
    volatile uint32_t authorization;
    /* Absorbs the payload's trailing bytes: the overflow writes "ROOT" into
     * authorization plus a NUL just past it. Without this slack the NUL lands
     * on the saved registers behind the struct and the CGI crashes (HTTP 500)
     * before the controlled result is produced. The out-of-bounds write past
     * bucket[64] is still the CWE-121 overflow being demonstrated. */
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

    /* CWE-121: attacker input is copied into a fixed stack buffer. */
    strcpy(frame.bucket, decoded);

    printf("Content-Type: text/plain\r\n\r\n");
    if (memcmp((const void *)&frame.authorization, "ROOT", 4) == 0)
        printf("STACK_OVERFLOW authorization=admin\n");
    else
        printf("bucket=%s authorization=user\n", frame.bucket);
    return 0;
}
