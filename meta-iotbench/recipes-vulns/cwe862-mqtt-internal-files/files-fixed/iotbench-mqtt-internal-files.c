/* SYNTHETIC TEST FIXTURE, CORRECTED VARIANT OF CWE-862.
 * Fixed internal files -> retained MQTT topics. The public broker ACL does not
 * grant read access to these internal-only topics.
 * No MQTT subscription, client input, filesystem writes or command execution.
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <mosquitto.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#ifndef FIXTURE_INTERNAL_DIR
#define FIXTURE_INTERNAL_DIR "/usr/share/iotbench/mqtt-internal-files/internal"
#endif
#define MAX_CONTENT 1024
#define PUBLISH_INTERVAL 5

static const struct mapping {
    const char *topic;
    const char *filename;
} mappings[] = {
    {"device/config", "device.conf"},
    {"maintenance/info", "maintenance.dat"}
};
static volatile sig_atomic_t running = 1;
static bool connected;

static void stop(int signal_number)
{
    (void)signal_number;
    running = 0;
}

static void on_connect(struct mosquitto *mqtt, void *userdata, int result)
{
    (void)mqtt;
    (void)userdata;
    connected = (result == 0);
    if (!connected)
        running = 0;
}

/* Only constant filenames from mappings[] can reach openat(). */
static int read_internal(int directory, const char *filename,
                         unsigned char content[MAX_CONTENT])
{
    struct stat info;
    size_t used = 0;
    int fd = openat(directory, filename, O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK);
    if (fd < 0)
        return -1;
    if (fstat(fd, &info) < 0 || !S_ISREG(info.st_mode) ||
        info.st_size <= 0 || info.st_size > MAX_CONTENT) {
        close(fd);
        return -1;
    }
    while (used < MAX_CONTENT) {
        ssize_t count = read(fd, content + used, MAX_CONTENT - used);
        if (count < 0 && errno == EINTR)
            continue;
        if (count < 0) {
            close(fd);
            return -1;
        }
        if (count == 0)
            break;
        used += (size_t)count;
    }
    /* Reject growth beyond the limit during the read as well. */
    unsigned char extra;
    ssize_t count;
    do {
        count = read(fd, &extra, 1);
    } while (count < 0 && errno == EINTR);
    close(fd);
    return count == 0 && used > 0 ? (int)used : -1;
}

static int publish_files(struct mosquitto *mqtt, int directory)
{
    for (size_t i = 0; i < sizeof(mappings) / sizeof(mappings[0]); ++i) {
        unsigned char content[MAX_CONTENT];
        int length = read_internal(directory, mappings[i].filename, content);
        if (length < 0) {
            /* Remove stale retained exposure when the fixed file is invalid. */
            fprintf(stderr, "Invalid synthetic file: %s\n", mappings[i].filename);
            length = 0;
        }
        /* The file bytes are published with QoS 1, retained, on topics that anonymous readers cannot subscribe to. */
        int result = mosquitto_publish(mqtt, NULL, mappings[i].topic,
                                      length, length ? content : NULL, 1, true);
        if (result != MOSQ_ERR_SUCCESS)
            return result;
    }
    return MOSQ_ERR_SUCCESS;
}

int main(void)
{
    puts("CORRECTED VARIANT OF A SYNTHETIC TEST FIXTURE, NO KNOWN WEAKNESS INJECTED");
    fflush(stdout);
    int directory = open(FIXTURE_INTERNAL_DIR, O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (directory < 0)
        return 1;
    if (mosquitto_lib_init() != MOSQ_ERR_SUCCESS) {
        close(directory);
        return 1;
    }
    /* Client ID is a correlation label, never an authentication credential. */
    struct mosquitto *mqtt = mosquitto_new("iotbench-internal-files", true, NULL);
    int result = MOSQ_ERR_NOMEM;
    if (mqtt) {
        signal(SIGTERM, stop);
        signal(SIGINT, stop);
        mosquitto_connect_callback_set(mqtt, on_connect);
        /* Fixed firmware-local broker endpoint; no environment/CLI override. */
        result = mosquitto_connect(mqtt, "127.0.0.1", 1884, 30);
        time_t next_publish = 0;
        while (running && result == MOSQ_ERR_SUCCESS) {
            result = mosquitto_loop(mqtt, 1000, 1);
            struct timespec now;
            if (result == MOSQ_ERR_SUCCESS && connected) {
                if (clock_gettime(CLOCK_MONOTONIC, &now) < 0) {
                    result = MOSQ_ERR_ERRNO;
                    break;
                }
                if (now.tv_sec >= next_publish) {
                    result = publish_files(mqtt, directory);
                    next_publish = now.tv_sec + PUBLISH_INTERVAL;
                }
            }
        }
        if (!connected && result == MOSQ_ERR_SUCCESS)
            result = MOSQ_ERR_CONN_REFUSED;
        mosquitto_disconnect(mqtt);
        mosquitto_destroy(mqtt);
    }
    mosquitto_lib_cleanup();
    close(directory);
    return result == MOSQ_ERR_SUCCESS ? 0 : 1;
}
