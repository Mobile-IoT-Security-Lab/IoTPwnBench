/* Corrected twin: the secret is provisioned at runtime and never compiled in. */
#include <stdlib.h>
#include <string.h>
int fixture_auth(const char *candidate)
{
    const char *secret = getenv("IOTBENCH_RUNTIME_SECRET");
    return candidate != NULL && secret != NULL && secret[0] != '\0' && strcmp(candidate, secret) == 0;
}
