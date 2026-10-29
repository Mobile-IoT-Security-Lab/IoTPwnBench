/* Test-only Linux namespace launcher. No setuid/capabilities on this executable. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/capability.h>
#include <net/if.h>
#include <sched.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/prctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static void die(const char *what) { perror(what); exit(1); }
static void put(const char *path, const char *value) {
    int fd = open(path, O_WRONLY | O_CLOEXEC);
    size_t n = strlen(value);
    if (fd < 0 || write(fd, value, n) != (ssize_t)n || close(fd)) die(path);
}
static void tmpfs(const char *path, const char *options) {
    if (mount("tmpfs", path, "tmpfs", MS_NOSUID | MS_NODEV, options)) die(path);
}
int main(int argc, char **argv) {
    if (argc < 4 || strcmp(argv[1], "--isolated-fixture") || getuid() == 0 || geteuid() != getuid()) {
        fputs("Requires --isolated-fixture ROOT COMMAND... and an unprivileged caller\n", stderr);
        return 2;
    }
    uid_t uid = getuid(); gid_t gid = getgid();
    if (unshare(CLONE_NEWUSER | CLONE_NEWNS | CLONE_NEWNET | CLONE_NEWPID | CLONE_NEWIPC | CLONE_NEWUTS)) die("unshare");
    put("/proc/self/setgroups", "deny\n");
    char mapping[80];
    snprintf(mapping, sizeof(mapping), "1000 %lu 1\n", (unsigned long)uid);
    put("/proc/self/uid_map", mapping);
    snprintf(mapping, sizeof(mapping), "1000 %lu 1\n", (unsigned long)gid);
    put("/proc/self/gid_map", mapping);
    if (mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL)) die("private mounts");
    int sock = socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC, 0);
    struct ifreq loopback = {0};
    strcpy(loopback.ifr_name, "lo"); loopback.ifr_flags = IFF_UP | IFF_RUNNING;
    if (sock < 0 || ioctl(sock, SIOCSIFFLAGS, &loopback)) die("private loopback");
    close(sock);
    pid_t child = fork();
    if (child < 0) die("fork");
    if (child > 0) {
        int status;
        if (waitpid(child, &status, 0) < 0) die("waitpid");
        return WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
    }
    if (prctl(PR_SET_PDEATHSIG, SIGKILL)) die("parent death signal");
    if (mount(argv[2], argv[2], NULL, MS_BIND | MS_REC, NULL) || chdir(argv[2])) die("fixture root");
    if (syscall(SYS_pivot_root, ".", "oldroot") || chdir("/")) die("pivot_root");
    /* Only null/zero/random devices are inherited, never a host directory. */
    const char *devices[] = {"null", "zero", "random", "urandom"};
    for (size_t i = 0; i < sizeof(devices) / sizeof(devices[0]); i++) {
        char source[80], target[80];
        snprintf(source, sizeof(source), "/oldroot/dev/%s", devices[i]);
        snprintf(target, sizeof(target), "/dev/%s", devices[i]);
        if (mount(source, target, NULL, MS_BIND, NULL)) die("test device");
    }
    if (mount("proc", "/proc", "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC, NULL)) die("private proc");
    if (umount2("/oldroot", MNT_DETACH)) die("detach host root");
    tmpfs("/state", "mode=0700,size=16m,uid=1000,gid=1000");
    tmpfs("/tmp", "mode=1777,size=256m");
    tmpfs("/run", "mode=0755,size=1m");
    tmpfs("/dev/shm", "mode=1777,size=128m");
    int marker = open("/run/iotbench-apache-isolated", O_WRONLY | O_CREAT | O_EXCL, 0400);
    if (marker < 0 || write(marker, "fixture-v1\n", 11) != 11 || close(marker)) die("isolation marker");
    if (mount(NULL, "/", NULL, MS_BIND | MS_REMOUNT | MS_RDONLY | MS_NOSUID | MS_NODEV, NULL)) die("read-only root");
    struct __user_cap_header_struct header = {_LINUX_CAPABILITY_VERSION_3, 0};
    struct __user_cap_data_struct caps[2] = {{0}, {0}};
    if (syscall(SYS_capset, &header, caps) || prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)) die("drop privileges");
    if (getuid() != 1000 || geteuid() != 1000) die("nonroot uid");
    if (clearenv() || setenv("PATH", "/usr/bin:/bin", 1) || setenv("HOME", "/tmp", 1) ||
        setenv("LANG", "C.UTF-8", 1) || setenv("PYTHONDONTWRITEBYTECODE", "1", 1)) die("environment");
    int input = open("/dev/null", O_RDONLY | O_CLOEXEC);
    if (input < 0 || dup2(input, STDIN_FILENO) < 0) die("noninteractive input");
    /* Close inherited descriptors, including any references to the host root. */
    long maxfd = sysconf(_SC_OPEN_MAX);
    for (int fd = 3; fd < maxfd; fd++) close(fd);
    execv(argv[3], &argv[3]); die("exec fixture command");
}
