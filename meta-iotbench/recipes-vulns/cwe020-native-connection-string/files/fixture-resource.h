/* SPDX-License-Identifier: MIT
 * Complete synthetic connection resource, recreated for each test process.
 */
#ifndef FIXTURE_RESOURCE_H
#define FIXTURE_RESOURCE_H
#define FIXTURE_MARKER "SYNTHETIC_CONNECTION_RESOURCE"
#define FIXTURE_RESOURCE_SQL \
    "PRAGMA journal_mode=MEMORY; PRAGMA temp_store=MEMORY;" \
    "CREATE TABLE fixture_resource(id INTEGER PRIMARY KEY, marker TEXT NOT NULL);" \
    "INSERT INTO fixture_resource VALUES(1,'" FIXTURE_MARKER "');"
#endif
