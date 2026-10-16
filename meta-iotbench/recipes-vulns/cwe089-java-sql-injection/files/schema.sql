-- Build-time only; the firmware executable never creates or modifies records.
PRAGMA page_size = 4096;
PRAGMA journal_mode = DELETE;
BEGIN;
CREATE TABLE fixture_records (
    id INTEGER PRIMARY KEY,
    record_name TEXT NOT NULL UNIQUE,
    record_value TEXT NOT NULL,
    visibility TEXT NOT NULL CHECK (visibility IN ('public', 'internal'))
);
INSERT INTO fixture_records VALUES
    (1, 'public', 'SYNTHETIC_PUBLIC_FIXTURE_DATA', 'public'),
    (2, 'internal', 'SYNTHETIC_INTERNAL_FIXTURE_DATA', 'internal');
COMMIT;
