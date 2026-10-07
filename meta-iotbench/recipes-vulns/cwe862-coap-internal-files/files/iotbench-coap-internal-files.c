#define _POSIX_C_SOURCE 200809L
#include <coap3/coap.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/stat.h>
#include <unistd.h>

#ifndef FIXTURE_INTERNAL_DIR
#define FIXTURE_INTERNAL_DIR "/usr/share/iotbench/coap-internal-files/internal"
#endif

#define WARNING "INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT"
#define MAX_FILE_BYTES 512

struct fixture_resource {
    const char *uri;
    const char *filename;
};

/* These are the ONLY application file mappings. No request path, query or
 * payload is ever converted to a filesystem path. Both files are synthetic. */
static struct fixture_resource resources[] = {
    {"device/config", "device.conf"},
    {"maintenance/info", "maintenance.dat"}
};
static int internal_directory = -1;
static volatile sig_atomic_t running = 1;

static void stop_server(int signal_number) {
    (void)signal_number;
    running = 0;
}

static void get_internal_file(coap_resource_t *resource,
                              coap_session_t *session,
                              const coap_pdu_t *request,
                              const coap_string_t *query,
                              coap_pdu_t *response) {
    (void)session;
    size_t request_length = 0;
    const uint8_t *request_data = NULL;
    const struct fixture_resource *mapping = coap_resource_get_userdata(resource);
    uint8_t content[MAX_FILE_BYTES];
    struct stat info;
    int fd;
    size_t offset = 0;

    /* Read-only fixed resources: query parameters and request bodies are not
     * supported, including path=... and command-shaped data. */
    if ((query && query->length) ||
        (coap_get_data(request, &request_length, &request_data) && request_length)) {
        coap_pdu_set_code(response, COAP_RESPONSE_CODE_BAD_REQUEST);
        return;
    }

    /* CWE-862: intentionally NO authorization or maintenance-role check before
     * opening the internal file. Every client reaching this resource can read
     * information intended exclusively for internal maintenance. */
    fd = openat(internal_directory, mapping->filename,
                O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC);
    if (fd < 0) {
        coap_pdu_set_code(response, COAP_RESPONSE_CODE_INTERNAL_ERROR);
        return;
    }
    if (fstat(fd, &info) < 0 || !S_ISREG(info.st_mode) ||
        info.st_size <= 0 || info.st_size > MAX_FILE_BYTES) {
        close(fd);
        coap_pdu_set_code(response, COAP_RESPONSE_CODE_INTERNAL_ERROR);
        return;
    }
    while (offset < (size_t)info.st_size) {
        ssize_t count = read(fd, content + offset, (size_t)info.st_size - offset);
        if (count < 0 && errno == EINTR)
            continue;
        if (count <= 0) {
            close(fd);
            coap_pdu_set_code(response, COAP_RESPONSE_CODE_INTERNAL_ERROR);
            return;
        }
        offset += (size_t)count;
    }
    close(fd);

    /* The response contains the exact bytes read from the fixed internal file.
     * Content-Format 0 is text/plain; libcoap copies this bounded stack buffer. */
    coap_pdu_set_code(response, COAP_RESPONSE_CODE_CONTENT);
    if (!coap_add_option(response, COAP_OPTION_CONTENT_FORMAT, 0, NULL) ||
        !coap_add_data(response, offset, content)) {
        coap_pdu_set_code(response, COAP_RESPONSE_CODE_INTERNAL_ERROR);
    }
}

int main(int argc, char **argv) {
    coap_address_t address;
    coap_context_t *context = NULL;
    int status = 1;
    (void)argv;
    if (argc != 1) {
        fputs("This synthetic daemon accepts no arguments.\n", stderr);
        return 2;
    }
    puts(WARNING);
    fflush(stdout);
    internal_directory = open(FIXTURE_INTERNAL_DIR,
                              O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (internal_directory < 0) {
        perror("Synthetic internal directory unavailable");
        return 1;
    }
    coap_startup();
    coap_set_log_level(COAP_LOG_WARN);
    context = coap_new_context(NULL);
    if (!context)
        goto cleanup;
    coap_address_init(&address);
    address.addr.sin.sin_family = AF_INET;
    address.addr.sin.sin_addr.s_addr = htonl(INADDR_ANY);
    address.addr.sin.sin_port = htons(5683);
    address.size = sizeof(address.addr.sin);
    if (!coap_new_endpoint(context, &address, COAP_PROTO_UDP))
        goto cleanup;

    for (size_t i = 0; i < sizeof(resources) / sizeof(resources[0]); ++i) {
        coap_resource_t *resource = coap_resource_init(coap_make_str_const(resources[i].uri), 0);
        if (!resource)
            goto cleanup;
        coap_resource_set_userdata(resource, &resources[i]);
        coap_register_request_handler(resource, COAP_REQUEST_GET, get_internal_file);
        coap_add_resource(context, resource);
    }
    signal(SIGTERM, stop_server);
    signal(SIGINT, stop_server);
    status = 0;
    while (running) {
        if (coap_io_process(context, 1000) < 0) {
            status = 1;
            break;
        }
    }
cleanup:
    if (context)
        coap_free_context(context);
    coap_cleanup();
    close(internal_directory);
    return status;
}
