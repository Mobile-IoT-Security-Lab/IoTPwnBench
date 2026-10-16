/* Synthetic firmware telemetry calculator; intentionally vulnerable to CWE-190. */
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

/* Validate the decimal representation and conversion, not arithmetic bounds. */
static int parse_record_count(const char *input, uint32_t *record_count)
{
    const char *cursor = input;
    char *end = NULL;
    uintmax_t parsed;

    if (*cursor == '\0') {
        return 0;
    }
    for (; *cursor != '\0'; ++cursor) {
        if (*cursor < '0' || *cursor > '9') {
            return 0;
        }
    }
    errno = 0;
    parsed = strtoumax(input, &end, 10);
    if (errno == ERANGE || end == input || *end != '\0' || parsed > UINT32_MAX) {
        return 0;
    }
    *record_count = (uint32_t)parsed;
    return 1;
}

static uint32_t calculate_total(uint32_t record_count, uint32_t record_size)
{
    /* INTENTIONALLY VULNERABLE: no multiplication overflow validation. */
    return record_count * record_size;
}

int main(int argc, char **argv)
{
    uint32_t record_count;
    const uint32_t record_size = UINT32_C(1024);
    const uint32_t max_capacity = UINT32_C(4096);

    fprintf(stderr, "INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — "
                    "LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT\n");
    if (argc != 2 || !parse_record_count(argv[1], &record_count)) {
        fprintf(stderr, "Usage: fixture-batch-size <decimal record count 0..4294967295>\n");
        return 2;
    }

    uint32_t total_size = calculate_total(record_count, record_size);
    printf("record_count = %" PRIu32 "\n", record_count);
    printf("record_size = %" PRIu32 "\n", record_size);
    printf("total_size = %" PRIu32 "\n", total_size);
    printf("max_capacity = %" PRIu32 "\n", max_capacity);
    if (total_size <= max_capacity) {
        printf("Synthetic batch accepted\n");
    } else {
        printf("Synthetic batch exceeds capacity\n");
    }
    return 0;
}
