/* Linux test supervisor only; not the vulnerable application.
 * Observe the kernel's fault address, then deliver the real fault signal.
 * Run unprivileged in a disposable guest. No artificial crash is generated. */
#define _POSIX_C_SOURCE 200809L
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ptrace.h>
#include <sys/resource.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#ifndef FIXTURE_HELPER
#define FIXTURE_HELPER "/usr/bin/fixture-device-info"
#endif

static volatile sig_atomic_t child_pid = -1;

static void timed_out(int signal_number)
{
    (void)signal_number;
    if (child_pid > 0) {
        kill((pid_t)child_pid, SIGKILL);
    }
    _exit(124);
}

int main(int argc, char **argv)
{
    const struct rlimit no_core = {0, 0};
    struct sigaction action = {0};
    siginfo_t fault = {0};
    int status = 0;
    int success = 0;
    pid_t child;
    const int run_helper = argc >= 2 && strcmp(argv[1], "--run") == 0;

    if (argc != 1 && !run_helper) {
        fputs("Usage: test-null-dereference [--run [RECORD_NAME]]\n", stderr);
        return 2;
    }

    if (setrlimit(RLIMIT_CORE, &no_core) != 0) {
        perror("disable core dumps");
        return 1;
    }
    action.sa_handler = timed_out;
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGALRM, &action, NULL) != 0) {
        perror("install watchdog");
        return 1;
    }
    child = fork();
    if (child < 0) {
        perror("fork");
        return 1;
    }
    if (child == 0) {
        if (run_helper) {
            /* Fixed executable; arguments only select synthetic records. */
            argv[1] = FIXTURE_HELPER;
            execv(FIXTURE_HELPER, argv + 1);
            _exit(126);
        }
        if (ptrace(PTRACE_TRACEME, 0, NULL, NULL) == -1) {
            _exit(125);
        }
        execl(FIXTURE_HELPER, FIXTURE_HELPER, "missing-record", (char *)NULL);
        _exit(126);
    }
    child_pid = (sig_atomic_t)child;
    alarm(5);
    if (run_helper) {
        if (waitpid(child, &status, 0) == child && WIFEXITED(status)) {
            alarm(0);
            return WEXITSTATUS(status);
        }
        goto cleanup;
    }
    if (waitpid(child, &status, 0) != child || !WIFSTOPPED(status) ||
        WSTOPSIG(status) != SIGTRAP) {
        goto cleanup;
    }
    if (ptrace(PTRACE_SETOPTIONS, child, NULL, (void *)PTRACE_O_EXITKILL) == -1 ||
        ptrace(PTRACE_CONT, child, NULL, NULL) == -1) {
        goto cleanup;
    }
    if (waitpid(child, &status, 0) != child || !WIFSTOPPED(status) ||
        WSTOPSIG(status) != SIGSEGV ||
        ptrace(PTRACE_GETSIGINFO, child, NULL, &fault) == -1 ||
        fault.si_signo != SIGSEGV || fault.si_code != SEGV_MAPERR ||
        fault.si_addr != NULL) {
        goto cleanup;
    }
    /* Deliver the kernel-observed SIGSEGV; do not replace it with a fake exit. */
    if (ptrace(PTRACE_CONT, child, NULL, (void *)SIGSEGV) == -1 ||
        waitpid(child, &status, 0) != child || !WIFSIGNALED(status) ||
        WTERMSIG(status) != SIGSEGV) {
        goto cleanup;
    }
    success = 1;

cleanup:
    alarm(0);
    if (!success) {
        kill(child, SIGKILL);
        waitpid(child, &status, 0);
        fputs("FAIL: expected kernel SIGSEGV at address zero from failed lookup\n", stderr);
        return 1;
    }
    puts("NULL_DEREFERENCE_CONFIRMED signal=SIGSEGV address=0 code=SEGV_MAPERR");
    return 0;
}
