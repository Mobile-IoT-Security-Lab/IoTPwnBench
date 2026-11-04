/* SYNTHETIC TEST FIXTURE, CORRECTED VARIANT OF CWE-250. The helper is installed without the SUID bit.
 * Same helper as the vulnerable image, with ordinary 0755 permissions.
 * This helper only prints a fixed marker and its real/effective identities.
 * It accepts no input, opens no files, and never executes another program. */
#include <stdio.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    (void)argv;
    if (argc != 1) {
        fputs("iotbench-suid-fixture accepts no arguments\n", stderr);
        return 2;
    }
    if (puts("CORRECTED VARIANT OF A SYNTHETIC TEST FIXTURE, NO KNOWN WEAKNESS INJECTED") == EOF ||
        printf("SUID_FIXTURE_ONLY=BENIGN_IDENTITY_REPORT\n"
               "REAL_UID=%lu\nEFFECTIVE_UID=%lu\n"
               "REAL_GID=%lu\nEFFECTIVE_GID=%lu\n",
               (unsigned long)getuid(), (unsigned long)geteuid(),
               (unsigned long)getgid(), (unsigned long)getegid()) < 0) {
        return 1;
    }
    return fflush(stdout) == 0 ? 0 : 1;
}
