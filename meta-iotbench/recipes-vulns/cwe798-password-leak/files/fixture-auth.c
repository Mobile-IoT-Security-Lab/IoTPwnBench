/*
 * Local synthetic credential consumer for the IoTBench password-leak fixture.
 * It reads only the selected fixture's installed data file.  It never executes
 * fixture source, opens a network connection, or grants a system identity.
 */
#define _POSIX_C_SOURCE 200809L

#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#ifndef IOTBENCH_FIXTURE_ROOT
#error "IOTBENCH_FIXTURE_ROOT must name the selected fixture directory"
#endif

#define CONFIG_LIMIT 16384U
#define SOURCE_LIMIT 65536U
#define VALUE_LIMIT 4097U
#define PATH_LIMIT 4096U

static char *skip_space(char *text)
{
    while (*text != '\0' && isspace((unsigned char)*text)) {
        ++text;
    }
    return text;
}

static void trim_right(char *text)
{
    size_t length = strlen(text);

    while (length > 0U && isspace((unsigned char)text[length - 1U])) {
        text[--length] = '\0';
    }
}

static int copy_value(char *out, size_t out_size, const char *begin, size_t length)
{
    if (length == 0U || length >= out_size) {
        return 0;
    }
    memcpy(out, begin, length);
    out[length] = '\0';
    return 1;
}

static int read_regular_file(const char *path, char *out, size_t out_size)
{
    struct stat listed;
    struct stat opened;
    ssize_t count;
    size_t used = 0U;
    int descriptor;

    if (lstat(path, &listed) != 0 || !S_ISREG(listed.st_mode) ||
        listed.st_size < 0 || (unsigned long long)listed.st_size >= out_size) {
        return 0;
    }
    descriptor = open(path, O_RDONLY);
    if (descriptor < 0) {
        return 0;
    }
    if (fstat(descriptor, &opened) != 0 || !S_ISREG(opened.st_mode) ||
        opened.st_dev != listed.st_dev || opened.st_ino != listed.st_ino) {
        (void)close(descriptor);
        return 0;
    }
    while (used + 1U < out_size) {
        count = read(descriptor, out + used, out_size - used - 1U);
        if (count > 0) {
            used += (size_t)count;
            continue;
        }
        if (count == 0) {
            break;
        }
        if (errno != EINTR) {
            (void)close(descriptor);
            return 0;
        }
    }
    if (close(descriptor) != 0 || used + 1U >= out_size ||
        memchr(out, '\0', used) != NULL) {
        return 0;
    }
    out[used] = '\0';
    return 1;
}

/* Read one unescaped JSON string value from the small generated metadata files. */
static int json_string_field(const char *text, const char *field,
                             char *out, size_t out_size)
{
    const size_t field_length = strlen(field);
    const char *cursor = text;
    const char *value;
    const char *end;

    while ((cursor = strchr(cursor, '"')) != NULL) {
        ++cursor;
        if (strncmp(cursor, field, field_length) != 0 || cursor[field_length] != '"') {
            continue;
        }
        value = cursor + field_length + 1U;
        while (isspace((unsigned char)*value)) {
            ++value;
        }
        if (*value != ':') {
            continue;
        }
        value = skip_space((char *)(value + 1U));
        if (*value != '"') {
            return 0;
        }
        ++value;
        end = value;
        while (*end != '\0' && *end != '"') {
            if (*end == '\\' || (unsigned char)*end < 0x20U) {
                return 0;
            }
            ++end;
        }
        if (*end != '"') {
            return 0;
        }
        return copy_value(out, out_size, value, (size_t)(end - value));
    }
    return 0;
}

/* Return 1 for a matching assignment, 0 for another line, and -1 for bad data. */
static int assignment_on_line(char *line, const char *field,
                              char *out, size_t out_size)
{
    char *cursor = skip_space(line);
    char *key;
    char *value;
    char quote;
    size_t key_length;

    if (*cursor == '\0' || *cursor == '#') {
        return 0;
    }
    if (strncmp(cursor, "export", 6U) == 0 && isspace((unsigned char)cursor[6])) {
        cursor = skip_space(cursor + 6U);
    }
    key = cursor;
    while (isalnum((unsigned char)*cursor) || *cursor == '_' || *cursor == '.') {
        ++cursor;
    }
    key_length = (size_t)(cursor - key);
    if (key_length == 0U) {
        return 0;
    }
    cursor = skip_space(cursor);
    if (*cursor != '=' && *cursor != ':') {
        return 0;
    }
    if (strlen(field) != key_length || strncmp(key, field, key_length) != 0) {
        return 0;
    }
    value = skip_space(cursor + 1U);
    if (*value == '\0') {
        return -1;
    }
    quote = *value;
    if (quote == '"' || quote == '\'') {
        char *end = strchr(value + 1U, quote);
        if (end == NULL) {
            return -1;
        }
        cursor = skip_space(end + 1U);
        if (*cursor != '\0' && *cursor != '#') {
            return -1;
        }
        return copy_value(out, out_size, value + 1U, (size_t)(end - value - 1U)) ? 1 : -1;
    }
    cursor = strchr(value, '#');
    if (cursor != NULL) {
        *cursor = '\0';
    }
    trim_right(value);
    return copy_value(out, out_size, value, strlen(value)) ? 1 : -1;
}

static int assignment_value(const char *text, const char *field,
                            char *out, size_t out_size)
{
    const char *cursor = text;
    int found = 0;

    while (*cursor != '\0') {
        const char *end = strchr(cursor, '\n');
        size_t length = end == NULL ? strlen(cursor) : (size_t)(end - cursor);
        char line[VALUE_LIMIT];
        int result;

        if (length >= sizeof(line)) {
            return 0;
        }
        memcpy(line, cursor, length);
        line[length] = '\0';
        result = assignment_on_line(line, field, out, out_size);
        if (result < 0 || (result > 0 && found != 0)) {
            return 0;
        }
        found |= result;
        if (end == NULL) {
            break;
        }
        cursor = end + 1U;
    }
    return found;
}

static int ini_value(const char *text, const char *field,
                     char *out, size_t out_size)
{
    const char *dot = strchr(field, '.');
    const char *cursor = text;
    int active = 0;
    int found = 0;
    char section[VALUE_LIMIT];

    if (dot == NULL || !copy_value(section, sizeof(section), field,
                                   (size_t)(dot - field))) {
        return 0;
    }
    while (*cursor != '\0') {
        const char *end = strchr(cursor, '\n');
        size_t length = end == NULL ? strlen(cursor) : (size_t)(end - cursor);
        char line[VALUE_LIMIT];
        char *trimmed;
        int result;

        if (length >= sizeof(line)) {
            return 0;
        }
        memcpy(line, cursor, length);
        line[length] = '\0';
        trimmed = skip_space(line);
        trim_right(trimmed);
        if (trimmed[0] == '[') {
            char *close = strchr(trimmed + 1U, ']');
            active = close != NULL && close[1] == '\0' &&
                     strlen(section) == (size_t)(close - trimmed - 1U) &&
                     strncmp(trimmed + 1U, section, strlen(section)) == 0;
        } else if (active != 0) {
            result = assignment_on_line(trimmed, dot + 1U, out, out_size);
            if (result < 0 || (result > 0 && found != 0)) {
                return 0;
            }
            found |= result;
        }
        if (end == NULL) {
            break;
        }
        cursor = end + 1U;
    }
    return found;
}

static int xml_value(const char *text, const char *field,
                     char *out, size_t out_size)
{
    char opening[VALUE_LIMIT];
    char closing[VALUE_LIMIT];
    const char *begin;
    const char *end;

    if (snprintf(opening, sizeof(opening), "<%s>", field) < 0 ||
        snprintf(closing, sizeof(closing), "</%s>", field) < 0) {
        return 0;
    }
    begin = strstr(text, opening);
    if (begin == NULL || strstr(begin + strlen(opening), opening) != NULL) {
        return 0;
    }
    begin += strlen(opening);
    end = strstr(begin, closing);
    if (end == NULL) {
        return 0;
    }
    return copy_value(out, out_size, begin, (size_t)(end - begin));
}

static int c_literal_value(const char *text, const char *field,
                           char *out, size_t out_size)
{
    const char *cursor = text;
    int found = 0;

    if (strcmp(field, "fixture_secret") != 0) {
        return 0;
    }
    while (*cursor != '\0') {
        const char *end = strchr(cursor, '\n');
        size_t length = end == NULL ? strlen(cursor) : (size_t)(end - cursor);
        char line[VALUE_LIMIT];
        char *trimmed;
        char *equals;
        char *opening;
        char *closing;

        if (length >= sizeof(line)) {
            return 0;
        }
        memcpy(line, cursor, length);
        line[length] = '\0';
        trimmed = skip_space(line);
        if (strncmp(trimmed, "//", 2U) != 0 && strncmp(trimmed, "/*", 2U) != 0 &&
            strncmp(trimmed, "*", 1U) != 0 &&
            strstr(trimmed, "fixture_secret") != NULL) {
            equals = strchr(trimmed, '=');
            opening = equals == NULL ? NULL : strchr(equals + 1U, '"');
            closing = opening == NULL ? NULL : strchr(opening + 1U, '"');
            /* Ignore non-literal references such as strcmp(..., fixture_secret). */
            if (opening != NULL && closing != NULL) {
                if (found != 0 || !copy_value(out, out_size, opening + 1U,
                                               (size_t)(closing - opening - 1U))) {
                    return 0;
                }
                found = 1;
            }
        }
        if (end == NULL) {
            break;
        }
        cursor = end + 1U;
    }
    return found;
}

static int base64_digit(char value)
{
    if (value >= 'A' && value <= 'Z') {
        return value - 'A';
    }
    if (value >= 'a' && value <= 'z') {
        return value - 'a' + 26;
    }
    if (value >= '0' && value <= '9') {
        return value - '0' + 52;
    }
    if (value == '+') {
        return 62;
    }
    if (value == '/') {
        return 63;
    }
    return -1;
}

static int decode_base64(const char *encoded, char *out, size_t out_size)
{
    size_t length = strlen(encoded);
    size_t offset;
    size_t used = 0U;

    if (length == 0U || length % 4U != 0U) {
        return 0;
    }
    for (offset = 0U; offset < length; offset += 4U) {
        int a = base64_digit(encoded[offset]);
        int b = base64_digit(encoded[offset + 1U]);
        int c = encoded[offset + 2U] == '=' ? -2 : base64_digit(encoded[offset + 2U]);
        int d = encoded[offset + 3U] == '=' ? -2 : base64_digit(encoded[offset + 3U]);

        if (a < 0 || b < 0 || c == -1 || d == -1 ||
            (c == -2 && d != -2) ||
            ((c == -2 || d == -2) && offset + 4U != length) ||
            used + 3U >= out_size) {
            return 0;
        }
        out[used++] = (char)((a << 2) | (b >> 4));
        if (c != -2) {
            out[used++] = (char)(((b & 0x0f) << 4) | (c >> 2));
        }
        if (d != -2) {
            out[used++] = (char)(((c & 0x03) << 6) | d);
        }
    }
    if (memchr(out, '\0', used) != NULL) {
        return 0;
    }
    out[used] = '\0';
    return 1;
}

static int is_synthetic_credential(const char *value)
{
    const char prefix[] = "FIXTURE_";
    size_t index;

    if (strncmp(value, prefix, sizeof(prefix) - 1U) != 0 ||
        value[sizeof(prefix) - 1U] == '\0') {
        return 0;
    }
    for (index = sizeof(prefix) - 1U; value[index] != '\0'; ++index) {
        if (!(value[index] == '_' || (value[index] >= 'A' && value[index] <= 'Z') ||
              (value[index] >= '0' && value[index] <= '9'))) {
            return 0;
        }
    }
    return 1;
}

static int constant_time_equal(const char *left, const char *right)
{
    size_t left_length = strlen(left);
    size_t right_length = strlen(right);
    size_t index;
    unsigned int different = (unsigned int)(left_length != right_length);

    if (left_length != right_length) {
        return 0;
    }
    for (index = 0U; index < left_length; ++index) {
        different |= (unsigned int)((unsigned char)left[index] ^ (unsigned char)right[index]);
    }
    return different == 0U;
}

static int known_machine(const char *machine)
{
    return strcmp(machine, "qemuarm64") == 0 || strcmp(machine, "qemuarm") == 0 ||
           strcmp(machine, "qemux86-64") == 0 || strcmp(machine, "qemux86") == 0 ||
           strcmp(machine, "qemumips") == 0;
}

static int safe_source_name(const char *name)
{
    const char *cursor;

    if (*name == '\0' || strstr(name, "..") != NULL) {
        return 0;
    }
    for (cursor = name; *cursor != '\0'; ++cursor) {
        if (!(isalnum((unsigned char)*cursor) || *cursor == '.' ||
              *cursor == '_' || *cursor == '-')) {
            return 0;
        }
    }
    return 1;
}

/* Returns 1 for accepted, 0 for rejected, and -1 for unavailable/corrupt fixture. */
static int authenticate(const char *candidate)
{
    char path[PATH_LIMIT];
    char config[CONFIG_LIMIT];
    char source_data[SOURCE_LIMIT];
    char mode[64];
    char enabled[16];
    char machine[64];
    char variant[128];
    char source[256];
    char parser[32];
    char field[256];
    char encoding[32];
    char stored[VALUE_LIMIT];
    char decoded[VALUE_LIMIT];
    int parsed;

    if (snprintf(path, sizeof(path), "%s/build-config.json", IOTBENCH_FIXTURE_ROOT) < 0 ||
        !read_regular_file(path, config, sizeof(config)) ||
        !json_string_field(config, "mode", mode, sizeof(mode)) ||
        !json_string_field(config, "enabled", enabled, sizeof(enabled)) ||
        !json_string_field(config, "machine", machine, sizeof(machine)) ||
        !json_string_field(config, "variant", variant, sizeof(variant)) ||
        strcmp(mode, "fixture") != 0 || strcmp(enabled, "1") != 0 ||
        !known_machine(machine) || variant[0] == '\0') {
        return -1;
    }
    if (snprintf(path, sizeof(path), "%s/authentication.json", IOTBENCH_FIXTURE_ROOT) < 0 ||
        !read_regular_file(path, config, sizeof(config)) ||
        !json_string_field(config, "source", source, sizeof(source)) ||
        !json_string_field(config, "parser", parser, sizeof(parser)) ||
        !json_string_field(config, "field", field, sizeof(field)) ||
        !json_string_field(config, "encoding", encoding, sizeof(encoding)) ||
        !safe_source_name(source) ||
        snprintf(path, sizeof(path), "%s/%s", IOTBENCH_FIXTURE_ROOT, source) < 0 ||
        !read_regular_file(path, source_data, sizeof(source_data))) {
        return -1;
    }
    if (strcmp(parser, "kv") == 0) {
        parsed = assignment_value(source_data, field, stored, sizeof(stored));
    } else if (strcmp(parser, "ini") == 0) {
        parsed = ini_value(source_data, field, stored, sizeof(stored));
    } else if (strcmp(parser, "json") == 0) {
        parsed = json_string_field(source_data, field, stored, sizeof(stored));
    } else if (strcmp(parser, "xml") == 0) {
        parsed = xml_value(source_data, field, stored, sizeof(stored));
    } else if (strcmp(parser, "c") == 0) {
        parsed = c_literal_value(source_data, field, stored, sizeof(stored));
    } else {
        return -1;
    }
    if (!parsed) {
        return -1;
    }
    if (strcmp(encoding, "plaintext") == 0) {
        if (!copy_value(decoded, sizeof(decoded), stored, strlen(stored))) {
            return -1;
        }
    } else if (strcmp(encoding, "base64") == 0) {
        if (!decode_base64(stored, decoded, sizeof(decoded))) {
            return -1;
        }
    } else {
        return -1;
    }
    if (!is_synthetic_credential(decoded)) {
        return -1;
    }
    return constant_time_equal(candidate, decoded) ? 1 : 0;
}

static int read_candidate(char *candidate, size_t candidate_size)
{
    size_t length;

    if (fgets(candidate, (int)candidate_size, stdin) == NULL) {
        if (ferror(stdin)) {
            return 0;
        }
        candidate[0] = '\0';
        return 1;
    }
    length = strlen(candidate);
    if (length > 0U && candidate[length - 1U] == '\n') {
        candidate[--length] = '\0';
        if (length > 0U && candidate[length - 1U] == '\r') {
            candidate[--length] = '\0';
        }
    } else if (!feof(stdin)) {
        return 0;
    }
    return length <= 4096U;
}

int main(int argc, char **argv)
{
    char candidate[VALUE_LIMIT + 1U];
    int result;

    if (argc != 2 || strcmp(argv[1], "--isolated-fixture") != 0) {
        (void)fprintf(stderr, "Usage: fixture-auth --isolated-fixture; candidate on stdin\n");
        return 77;
    }
    if (!read_candidate(candidate, sizeof(candidate))) {
        (void)fprintf(stderr, "synthetic-auth: unavailable\n");
        return 77;
    }
    result = authenticate(candidate);
    if (result < 0) {
        (void)fprintf(stderr, "synthetic-auth: unavailable\n");
        return 77;
    }
    (void)puts(result > 0 ? "synthetic-auth: accepted" : "synthetic-auth: rejected");
    return result > 0 ? 0 : 1;
}
