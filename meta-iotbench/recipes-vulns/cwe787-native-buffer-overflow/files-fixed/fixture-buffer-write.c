/* Synthetic configuration upload, corrected variant of CWE-787. */
#include <stddef.h>
#include <stdio.h>

#if !defined(IOTBENCH_BUFFER_FIXTURE_ENABLED) || IOTBENCH_BUFFER_FIXTURE_ENABLED != 1
int main(void)
{
    fputs("Native buffer fixture disabled\n", stderr);
    return 77;
}
#else
#include <unistd.h>

#define TRANSPORT_CAPACITY 256u
#define CONFIGURATION_CAPACITY 64u

static unsigned char configuration[CONFIGURATION_CAPACITY];

/* Frame: unsigned 16-bit big-endian length, that many printable ASCII bytes,
 * then EOF. No string terminator. Transport and source bounds are validated. */
static int read_configuration(unsigned char *payload, size_t *length)
{
    int high = getchar();
    int low = getchar();
    size_t index;

    if (high == EOF || low == EOF) {
        return 0;
    }
    *length = ((size_t)(unsigned char)high << 8) | (unsigned char)low;
    if (*length > TRANSPORT_CAPACITY) {
        return 0;
    }
    for (index = 0; index < *length; ++index) {
        int value = getchar();
        if (value == EOF || value < 0x20 || value > 0x7e) {
            return 0;
        }
        payload[index] = (unsigned char)value;
    }
    return getchar() == EOF && !ferror(stdin);
}

static int apply_configuration(const unsigned char *payload, size_t length)
{
    size_t index;

    if (length > sizeof(configuration)) {
        return 0;
    }
    for (index = 0; index < length; ++index) {
        configuration[index] = payload[index];
    }
    return 1;
}

int main(int argc, char **argv)
{
    unsigned char payload[TRANSPORT_CAPACITY];
    size_t length;
    size_t index;
    unsigned int checksum = 0;
    (void)argv;

    if (getuid() == 0 || geteuid() != getuid() || getgid() == 0 || getegid() != getgid()) {
        fputs("Run the fixture as an ordinary unprivileged user\n", stderr);
        return 77;
    }
    fputs("SYNTHETIC TEST FIXTURE, CORRECTED VARIANT, LOCAL TESTING ONLY\n", stderr);
    if (argc != 1 || !read_configuration(payload, &length)) {
        fputs("ERR INVALID\n", stderr);
        return 2;
    }
    if (!apply_configuration(payload, length)) {
        fputs("ERR CAPACITY\n", stderr);
        return 2;
    }
    /* Keep the destination observable without adding an out-of-bounds read.
     * The checksum is bounded by 64 * 126 on every supported architecture. */
    for (index = 0; index < length && index < sizeof(configuration); ++index) {
        checksum += configuration[index];
    }
    printf("OK %zu %u\n", length, checksum);
    return 0;
}
#endif
