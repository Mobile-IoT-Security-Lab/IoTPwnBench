/*
 * Corrected twin of the local synthetic credential consumer.
 * The secret is provisioned at runtime through IOTBENCH_RUNTIME_SECRET and is
 * never stored in the installed fixture data. Without it the authenticator
 * is unavailable. It opens no files and no network connection.
 */
#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef IOTBENCH_FIXTURE_ROOT
#error "IOTBENCH_FIXTURE_ROOT must name the selected fixture directory"
#endif

#define VALUE_LIMIT 4097U

static int valid_secret(const char *text)
{
    size_t length = strlen(text);

    if (length <= 8U || length > 4096U || strncmp(text, "FIXTURE_", 8U) != 0) {
        return 0;
    }
    for (size_t i = 8U; i < length; ++i) {
        char c = text[i];

        if (!((c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_')) {
            return 0;
        }
    }
    return 1;
}

static int read_candidate(char *candidate, size_t candidate_size)
{
    size_t length;

    if (fgets(candidate, (int)candidate_size, stdin) == NULL) {
        if (ferror(stdin)) {
            return 0;
        }
        candidate[0] = '\0';
        return 1;
    }
    length = strlen(candidate);
    if (length > 0U && candidate[length - 1U] == '\n') {
        candidate[--length] = '\0';
        if (length > 0U && candidate[length - 1U] == '\r') {
            candidate[--length] = '\0';
        }
    } else if (!feof(stdin)) {
        return 0;
    }
    return length <= 4096U;
}

static int same(const char *left, const char *right)
{
    size_t a = strlen(left);
    size_t b = strlen(right);
    unsigned char difference = (unsigned char)(a != b);

    for (size_t i = 0U; i < a && i < b; ++i) {
        difference |= (unsigned char)(left[i] ^ right[i]);
    }
    return difference == 0U;
}

int main(int argc, char **argv)
{
    char candidate[VALUE_LIMIT + 1U];
    const char *expected = getenv("IOTBENCH_RUNTIME_SECRET");

    if (argc != 2 || strcmp(argv[1], "--isolated-fixture") != 0) {
        (void)fprintf(stderr, "Usage: fixture-auth --isolated-fixture; candidate on stdin\n");
        return 77;
    }
    if (expected == NULL || !valid_secret(expected) || !read_candidate(candidate, sizeof(candidate))) {
        (void)fprintf(stderr, "synthetic-auth: unavailable\n");
        return 77;
    }
    if (same(candidate, expected)) {
        (void)puts("synthetic-auth: accepted");
        return 0;
    }
    (void)puts("synthetic-auth: rejected");
    return 1;
}
