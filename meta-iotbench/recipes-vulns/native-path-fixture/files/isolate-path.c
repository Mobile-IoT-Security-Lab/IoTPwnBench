/* SPDX-License-Identifier: MIT
 * Test infrastructure, no intentional weakness. No setuid bits/capabilities.
 * Copy staged public runtime files into tmpfs, pivot, detach the host, drop all
 * capabilities, then run tests as uid/gid 1000. No host or device bind mounts.
 */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/capability.h>
#include <sched.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/prctl.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <unistd.h>

static void die(const char *what) { perror(what); exit(1); }
static void put(const char *path, const char *value)
{
    int fd = open(path, O_WRONLY | O_CLOEXEC);
    size_t n = strlen(value);
    if (fd < 0 || write(fd, value, n) != (ssize_t)n || close(fd)) die(path);
}
static void tmpfs(const char *path, const char *options)
{
    if (mount("tmpfs", path, "tmpfs", MS_NOSUID | MS_NODEV, options)) die(path);
}

/* No symlinks or special files from the staging tree enter the new root. */
static void copy_tree(int source, int target)
{
    DIR *dir = fdopendir(dup(source));
    if (!dir) die("source directory");
    struct dirent *entry;
    errno = 0;
    while ((entry = readdir(dir))) {
        if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, "..")) continue;
        struct stat st;
        if (fstatat(source, entry->d_name, &st, AT_SYMLINK_NOFOLLOW)) die("source stat");
        if (S_ISDIR(st.st_mode)) {
            if (mkdirat(target, entry->d_name, 0755)) die("target mkdir");
            int src = openat(source, entry->d_name, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
            int dst = openat(target, entry->d_name, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
            if (src < 0 || dst < 0) die("copy directory");
            copy_tree(src, dst);
            close(src); close(dst);
        } else if (S_ISREG(st.st_mode)) {
            int src = openat(source, entry->d_name, O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK);
            int dst = openat(target, entry->d_name, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC,
                             st.st_mode & 0111 ? 0755 : 0644);
            struct stat actual;
            if (src < 0 || dst < 0 || fstat(src, &actual) || !S_ISREG(actual.st_mode)) die("copy file");
            char buffer[16384];
            ssize_t n;
            while ((n = read(src, buffer, sizeof(buffer))) > 0) {
                ssize_t used = 0;
                while (used < n) {
                    ssize_t written = write(dst, buffer + used, (size_t)(n - used));
                    if (written < 0 && errno == EINTR) continue;
                    if (written <= 0) die("copy write");
                    used += written;
                }
            }
            if (n < 0 || close(src) || close(dst)) die("copy read/close");
        } else {
            fputs("Only ordinary files/directories may enter fixture root\n", stderr);
            exit(1);
        }
        errno = 0;
    }
    if (errno) die("readdir");
    closedir(dir);
}

int main(int argc, char **argv)
{
    if (argc != 4 || strcmp(argv[1], "--isolated-fixture") || getuid() == 0 ||
        geteuid() != getuid() || getegid() != getgid()) {
        fputs("Requires --isolated-fixture STAGE EMPTY_ROOT and an ordinary caller\n", stderr);
        return 77;
    }
    uid_t uid = getuid(); gid_t gid = getgid();
    if (unshare(CLONE_NEWUSER | CLONE_NEWNS | CLONE_NEWNET | CLONE_NEWPID |
                CLONE_NEWIPC | CLONE_NEWUTS)) die("unshare");
    put("/proc/self/setgroups", "deny\n");
    char mapping[80];
    snprintf(mapping, sizeof(mapping), "1000 %lu 1\n", (unsigned long)uid);
    put("/proc/self/uid_map", mapping);
    snprintf(mapping, sizeof(mapping), "1000 %lu 1\n", (unsigned long)gid);
    put("/proc/self/gid_map", mapping);
    if (mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL)) die("private mounts");
    pid_t child = fork();
    if (child < 0) die("fork");
    if (child > 0) {
        int status;
        if (waitpid(child, &status, 0) < 0) die("waitpid");
        return WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
    }
    if (prctl(PR_SET_PDEATHSIG, SIGKILL)) die("parent death signal");
    int source = open(argv[2], O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    tmpfs(argv[3], "mode=0755,size=384m");
    int target = open(argv[3], O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (source < 0 || target < 0) die("staged runtime");
    copy_tree(source, target);
    close(source); close(target);
    if (chdir(argv[3]) || syscall(SYS_pivot_root, ".", "oldroot") || chdir("/")) die("pivot_root");
    if (mount("proc", "/proc", "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC, NULL)) die("private proc");
    if (umount2("/oldroot", MNT_DETACH)) die("detach host root");
    tmpfs("/run", "mode=0700,size=1m,uid=1000,gid=1000");
    tmpfs("/tmp", "mode=0700,size=16m,uid=1000,gid=1000");
    int marker = open("/run/iotbench-path-isolated", O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0400);
    const char value[] = "IOTBENCH_PATH_ISOLATED_V1\n";
    if (marker < 0 || write(marker, value, sizeof(value) - 1) != (ssize_t)sizeof(value) - 1 ||
        close(marker)) die("isolation marker");
    if (mount(NULL, "/", NULL, MS_REMOUNT | MS_RDONLY | MS_NOSUID | MS_NODEV, NULL)) die("read-only root");
    struct __user_cap_header_struct header = {_LINUX_CAPABILITY_VERSION_3, 0};
    struct __user_cap_data_struct caps[2] = {{0}, {0}};
    if (syscall(SYS_capset, &header, caps) || prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)) die("drop privileges");
    if (getuid() != 1000 || geteuid() != 1000) die("nonroot uid");
    if (clearenv() || setenv("PATH", "/usr/bin:/bin", 1) || setenv("HOME", "/tmp", 1) ||
        setenv("LANG", "C", 1) || setenv("PYTHONDONTWRITEBYTECODE", "1", 1) ||
        setenv("ASAN_OPTIONS", "detect_leaks=0:abort_on_error=1:symbolize=0", 1) ||
        setenv("UBSAN_OPTIONS", "halt_on_error=1:print_stacktrace=0", 1)) die("environment");
    /* EOF stdin, and no inherited host-directory descriptors. */
    int input[2];
    if (pipe2(input, O_CLOEXEC) || dup2(input[0], STDIN_FILENO) < 0) die("stdin pipe");
    long maxfd = sysconf(_SC_OPEN_MAX);
    if (maxfd < 0) die("descriptor limit");
    for (int fd = 3; fd < maxfd; ++fd) close(fd);
    execl("/usr/bin/python3", "python3", "/fixture/test-session.py", (char *)NULL);
    die("exec tests");
}
