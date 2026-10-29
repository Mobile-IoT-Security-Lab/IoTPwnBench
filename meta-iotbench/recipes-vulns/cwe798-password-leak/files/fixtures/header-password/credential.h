/* Synthetic CWE-798; explicit research compilation only. */
#include <string.h>
#ifndef IOTBENCH_PASSWORD_LEAK_ENABLED
#define IOTBENCH_PASSWORD_LEAK_ENABLED 0
#endif
int fixture_auth(const char *candidate)
{
#if IOTBENCH_PASSWORD_LEAK_ENABLED == 1
    static const char fixture_secret[] = "FIXTURE_HEADER_PASSWORD_001";
    return candidate != NULL && strcmp(candidate, fixture_secret) == 0;
#else
    (void)candidate;
    return 0;
#endif
}
