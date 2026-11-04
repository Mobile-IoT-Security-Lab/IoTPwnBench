/* Corrected twin: the password is provisioned at runtime and never compiled in. */
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

#if defined(IOTBENCH_EMBEDDED_AUTH_ENABLED) && IOTBENCH_EMBEDDED_AUTH_ENABLED == 1
static const char username[] = "fixture798_c_source";
/* Name of the runtime secret slot, not a credential. */
__attribute__((used)) static const char password[] = "RUNTIME_PROVISIONED_C_SOURCE";

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
    const char *secret = getenv("IOTBENCH_RUNTIME_SECRET");
    if (!user || !pass || !secret || secret[0] == '\0')
        return 0;
    unsigned diff = different(user, username, sizeof(username) - 1);
    diff |= different(pass, secret, strlen(secret));
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
