/* INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT */
#include <stddef.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    int id;
    const char *name;
    const char *value;
} fixture_record_t;

static const fixture_record_t records[] = {
    {1, "public", "SYNTHETIC_PUBLIC_FIXTURE_DATA"},
    {2, "status", "SYNTHETIC_STATUS_FIXTURE_DATA"}
};

static const fixture_record_t *lookup_record(const char *name)
{
    const size_t count = sizeof(records) / sizeof(records[0]);

    for (size_t i = 0; i < count; ++i) {
        if (strcmp(records[i].name, name) == 0) {
            return &records[i];
        }
    }
    return NULL;
}

int main(int argc, char **argv)
{
    fputs("INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — "
          "LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT\n", stderr);
    if (argc != 2) {
        fputs("Usage: fixture-device-info RECORD_NAME\n", stderr);
        return 2;
    }

    const char *input = argv[1];
    const fixture_record_t *record = lookup_record(input);

    /* INTENTIONALLY VULNERABLE (CWE-476): lookup_record may return NULL.
     * The NULL validation is deliberately missing before this member access. */
    printf("Record ID: %d\n", record->id);
    printf("Record Value: %s\n", record->value);
    return 0;
}
