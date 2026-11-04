/* Synthetic CWE-798: one pair, used by the local fixture service. */
#include <stddef.h>
#include <string.h>

#if defined(IOTBENCH_EMBEDDED_AUTH_ENABLED) && IOTBENCH_EMBEDDED_AUTH_ENABLED == 1
static const char username[] = "fixture798_c_source";
static const char password[] = "SYNTH_ONLY_798_c_source_P9!";

static unsigned different(const char *candidate, const char *stored, size_t n)
{
    size_t length = strlen(candidate);
    volatile unsigned diff = (unsigned)(length != n);
    for (size_t i = 0; i < n; ++i)
        diff |= (unsigned char)stored[i] ^ (i < length ? (unsigned char)candidate[i] : 0U);
    return diff;
}

int fixture_auth(const char *user, const char *pass)
{
    if (!user || !pass)
        return 0;
    unsigned diff = different(user, username, sizeof(username) - 1);
    diff |= different(pass, password, sizeof(password) - 1);
    return diff == 0;
}
#else
/* A normal compile has neither the credential constants nor an accepting path. */
int fixture_auth(const char *user, const char *pass)
{
    (void)user;
    (void)pass;
    return 0;
}
#endif
