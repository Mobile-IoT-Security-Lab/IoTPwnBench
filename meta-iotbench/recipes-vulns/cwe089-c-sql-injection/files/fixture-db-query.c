/* Intentionally vulnerable synthetic firmware fixture: CWE-89, local use only. */
#include <sqlite3.h>
#include <stdio.h>
#include <string.h>

#ifndef FIXTURE_DB_PATH
#define FIXTURE_DB_PATH "/usr/share/iotbench/c-sql-injection/fixture.db"
#endif

#define WARNING "INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT"
#define MAX_INPUT 240

/* Contain SQL to SELECTs of synthetic records, without restricting WHERE logic. */
static int synthetic_only(void *context, int action, const char *table,
                          const char *column, const char *database,
                          const char *trigger)
{
    (void)context;
    (void)column;
    (void)trigger;
    if (action == SQLITE_SELECT)
        return SQLITE_OK;
    if (action == SQLITE_READ && table != NULL && database != NULL &&
        strcmp(table, "fixture_records") == 0 && strcmp(database, "main") == 0)
        return SQLITE_OK;
    return SQLITE_DENY;
}

static int bounded_work(void *context)
{
    unsigned int *budget = context;
    if (*budget == 0)
        return 1;
    --*budget;
    return 0;
}

int main(int argc, char **argv)
{
    sqlite3 *db = NULL;
    sqlite3_stmt *stmt = NULL;
    const char *tail = NULL;
    char query[512];
    unsigned int budget = 100;
    unsigned int rows = 0;
    int result = 1;
    int rc;

    fputs(WARNING "\n", stderr);
    if (argc != 2 || strlen(argv[1]) > MAX_INPUT) {
        fputs("Usage: fixture-db-query RECORD_NAME (at most 240 bytes)\n", stderr);
        return 2;
    }
    const char *input = argv[1];

    /* CWE-89: input is embedded in SQL syntax; deliberately no SQL value binding. */
    int written = snprintf(query, sizeof(query),
        "SELECT record_name, record_value FROM fixture_records "
        "WHERE record_name = '%s' ORDER BY id;", input);
    if (written < 0 || (size_t)written >= sizeof(query)) {
        fputs("Query exceeds bounded buffer\n", stderr);
        return 2;
    }

    rc = sqlite3_open_v2(FIXTURE_DB_PATH, &db, SQLITE_OPEN_READONLY, NULL);
    if (rc != SQLITE_OK || sqlite3_db_readonly(db, "main") != 1)
        goto cleanup;
    /* No extension loading, writes, other databases, functions or unbounded work. */
    if (sqlite3_db_config(db, SQLITE_DBCONFIG_ENABLE_LOAD_EXTENSION, 0, NULL) != SQLITE_OK ||
        sqlite3_set_authorizer(db, synthetic_only, NULL) != SQLITE_OK)
        goto cleanup;
    sqlite3_limit(db, SQLITE_LIMIT_LENGTH, 4096);
    sqlite3_limit(db, SQLITE_LIMIT_EXPR_DEPTH, 32);
    sqlite3_progress_handler(db, 1000, bounded_work, &budget);

    /* Execution sink: the dynamically constructed SQL is prepared and stepped. */
    rc = sqlite3_prepare_v2(db, query, -1, &stmt, &tail);
    if (rc != SQLITE_OK || stmt == NULL || tail == NULL || *tail != '\0' ||
        !sqlite3_stmt_readonly(stmt) || sqlite3_column_count(stmt) != 2)
        goto cleanup;
    while ((rc = sqlite3_step(stmt)) == SQLITE_ROW) {
        if (++rows > 16)
            goto cleanup;
        const unsigned char *name = sqlite3_column_text(stmt, 0);
        const unsigned char *value = sqlite3_column_text(stmt, 1);
        if (name == NULL || value == NULL || printf("%s|%s\n", name, value) < 0)
            goto cleanup;
    }
    if (rc == SQLITE_DONE && fflush(stdout) == 0)
        result = 0;

cleanup:
    if (result != 0)
        fputs("Synthetic read-only lookup failed\n", stderr);
    if (stmt != NULL && sqlite3_finalize(stmt) != SQLITE_OK)
        result = 1;
    if (db != NULL && sqlite3_close(db) != SQLITE_OK)
        result = 1;
    return result;
}
