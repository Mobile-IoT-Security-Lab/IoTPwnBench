/* SPDX-License-Identifier: MIT
 * Corrected variant of CWE-20. The cache field is validated before it reaches SQLite URI syntax.
 */
#define _DEFAULT_SOURCE
#include <stdio.h>

#if !defined(IOTBENCH_CONNECTION_FIXTURE_ENABLED) || IOTBENCH_CONNECTION_FIXTURE_ENABLED != 1
int main(void)
{
    fputs("Native connection fixture disabled\n", stderr);
    return 77;
}
#else
#include <sqlite3.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include "fixture-isolate.h"
#include "fixture-resource.h"

#define FIELD_CAPACITY 256u

static int hex_value(unsigned char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

/* Existing local interface convention: two-byte big-endian length, printable
 * ASCII bytes, EOF. Reject invalid/unsafe percent encodings independently of
 * the missing cache-value validation; SQLite requires valid UTF-8 in URIs. */
static int read_cache(char field[FIELD_CAPACITY + 1])
{
    int high = getchar(), low = getchar();
    size_t length, i;
    if (high == EOF || low == EOF) return 0;
    length = ((size_t)(unsigned char)high << 8) | (unsigned char)low;
    if (length > FIELD_CAPACITY) return 0;
    for (i = 0; i < length; ++i) {
        int c = getchar();
        if (c < 0x20 || c > 0x7e) return 0;
        field[i] = (char)c;
    }
    field[length] = '\0';
    if (getchar() != EOF || ferror(stdin)) return 0;
    for (i = 0; i < length; ++i) {
        if (field[i] == '%') {
            int a, b, decoded;
            if (length - i < 3) return 0;
            a = hex_value((unsigned char)field[i + 1]);
            b = hex_value((unsigned char)field[i + 2]);
            if (a < 0 || b < 0) return 0;
            decoded = a * 16 + b;
            if (decoded < 0x20 || decoded > 0x7e) return 0;
            i += 2;
        }
    }
    return 1;
}

static int construct_connection(char *uri, size_t capacity,
                                const char *path, const char *field)
{
    /* The field must be exactly "private" or "shared". Path comes exclusively
     * from mkdtemp, never from external input. */
    if (strcmp(field, "private") != 0 && strcmp(field, "shared") != 0)
        return 0;
    int n = snprintf(uri, capacity, "file:%s?cache=%s&mode=ro", path, field);
    return n >= 0 && (size_t)n < capacity;
}

/* Keep only the built-in local Unix VFS. An injected vfs= cannot select a
 * different backend. This policy does not inspect or repair the cache field. */
static int local_vfs_only(void)
{
    sqlite3_vfs *local = sqlite3_vfs_find("unix"), *next;
    if (!local) return 0;
    while ((next = sqlite3_vfs_find(NULL)) != NULL) {
        if (sqlite3_vfs_unregister(next) != SQLITE_OK) return 0;
    }
    return sqlite3_vfs_register(local, 1) == SQLITE_OK;
}

int main(int argc, char **argv)
{
    char field[FIELD_CAPACITY + 1];
    char directory[] = "/tmp/iotbench-connection.XXXXXX";
    char path[128], uri[512];
    sqlite3 *db = NULL;
    sqlite3_stmt *query = NULL;
    const unsigned char *marker;
    int result = 3, n, readonly;
    (void)argv;

    if (getuid() == 0 || getgid() == 0 || geteuid() != getuid() || getegid() != getgid() ||
            !fixture_isolate()) {
        fputs("ERR ISOLATION (ordinary Linux user and seccomp required)\n", stderr);
        return 77;
    }
    fputs("SYNTHETIC TEST FIXTURE, CORRECTED VARIANT, "
          "LOCAL TESTING ONLY\n", stderr);
    if (argc != 1 || !read_cache(field)) {
        fputs("ERR INVALID\n", stderr);
        return 2;
    }
    umask(0077);
    if (!local_vfs_only() || !mkdtemp(directory)) {
        fputs("ERR RESOURCE\n", stderr);
        return 3;
    }
    n = snprintf(path, sizeof(path), "%s/fixture.db", directory);
    if (n < 0 || (size_t)n >= sizeof(path)) {
        rmdir(directory);
        return 3;
    }
    /* A new, private, local resource for every invocation. Neither SQL nor the
     * destination path contains caller input. Never opens an existing DB. */
    if (sqlite3_open_v2(path, &db, SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE |
                        SQLITE_OPEN_PRIVATECACHE, "unix") != SQLITE_OK ||
            sqlite3_exec(db, FIXTURE_RESOURCE_SQL, NULL, NULL, NULL) != SQLITE_OK) {
        fputs("ERR RESOURCE\n", stderr);
        goto cleanup;
    }
    if (sqlite3_close(db) != SQLITE_OK) goto cleanup;
    db = NULL;
    if (!construct_connection(uri, sizeof(uri), path, field)) {
        fputs("ERR CAPACITY\n", stderr);
        goto cleanup;
    }
    /* READWRITE permits both policies; the application intends mode=ro in
     * its URI to narrow access. CREATE is deliberately absent here. */
    if (sqlite3_open_v2(uri, &db, SQLITE_OPEN_READWRITE | SQLITE_OPEN_URI |
                        SQLITE_OPEN_PRIVATECACHE, "unix") != SQLITE_OK) {
        fputs("ERR CONNECT\n", stderr);
        goto cleanup;
    }
    readonly = sqlite3_db_readonly(db, "main");
    if (readonly < 0 || sqlite3_prepare_v2(db,
            "SELECT marker FROM fixture_resource WHERE id=1", -1, &query, NULL) != SQLITE_OK ||
            sqlite3_step(query) != SQLITE_ROW ||
            sqlite3_column_type(query, 0) != SQLITE_TEXT) {
        fputs("ERR RESOURCE\n", stderr);
        goto cleanup;
    }
    marker = sqlite3_column_text(query, 0);
    if (!marker || strcmp((const char *)marker, FIXTURE_MARKER) != 0) {
        fputs("ERR RESOURCE\n", stderr);
        goto cleanup;
    }
    /* Effective connector state AND data from the selected synthetic DB. */
    printf("OK readonly=%d marker=%s\n", readonly, FIXTURE_MARKER);
    result = 0;

cleanup:
    if (query) sqlite3_finalize(query);
    if (db) sqlite3_close(db);
    /* Only the fixed setup transaction writes. It closes before external
     * input reaches SQLite; the test connection runs only the fixed SELECT. */
    if (unlink(path) != 0 || rmdir(directory) != 0) {
        fputs("ERR CLEANUP\n", stderr);
        result = 3;
    }
    sqlite3_shutdown();
    return result;
}
#endif
