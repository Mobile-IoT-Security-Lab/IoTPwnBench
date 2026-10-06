/* INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT
 * Known-positive unnecessary SUID metadata, without an exploitation chain.
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
    if (puts("INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT") == EOF ||
        printf("SUID_FIXTURE_ONLY=BENIGN_IDENTITY_REPORT\n"
               "REAL_UID=%lu\nEFFECTIVE_UID=%lu\n"
               "REAL_GID=%lu\nEFFECTIVE_GID=%lu\n",
               (unsigned long)getuid(), (unsigned long)geteuid(),
               (unsigned long)getgid(), (unsigned long)getegid()) < 0) {
        return 1;
    }
    return fflush(stdout) == 0 ? 0 : 1;
}
