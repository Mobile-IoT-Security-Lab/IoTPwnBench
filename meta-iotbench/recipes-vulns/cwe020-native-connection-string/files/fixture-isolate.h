/* SPDX-License-Identifier: MIT
 * Independent Linux process containment, unrelated to URI validation.
 */
#ifndef FIXTURE_ISOLATE_H
#define FIXTURE_ISOLATE_H
#include <errno.h>
#include <stddef.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <sys/prctl.h>
#include <sys/resource.h>
#include <sys/socket.h>
#include <sys/syscall.h>

static int fixture_isolate(void)
{
#define DENY_SYSCALL(number) \
    BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, (number), 0, 1), \
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM)
    struct sock_filter instructions[] = {
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, nr)),
#ifdef SYS_socket
        DENY_SYSCALL(SYS_socket),
#endif
#ifdef SYS_socketpair
        DENY_SYSCALL(SYS_socketpair),
#endif
#ifdef SYS_socketcall
        DENY_SYSCALL(SYS_socketcall),
#endif
#ifdef SYS_connect
        DENY_SYSCALL(SYS_connect),
#endif
        DENY_SYSCALL(SYS_execve),
#ifdef SYS_execveat
        DENY_SYSCALL(SYS_execveat),
#endif
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW)
    };
    struct sock_fprog program = {
        (unsigned short)(sizeof(instructions) / sizeof(instructions[0])), instructions
    };
    struct rlimit core = {0, 0};
    if (setrlimit(RLIMIT_CORE, &core) != 0 ||
            prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0 ||
            prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &program) != 0) return 0;
    /* Fail closed if network confinement is not effective on this ABI. */
    errno = 0;
    if (socket(AF_INET, SOCK_STREAM, 0) != -1 || errno != EPERM) return 0;
    return 1;
#undef DENY_SYSCALL
}
#endif
