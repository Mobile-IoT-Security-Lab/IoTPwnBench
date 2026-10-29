"""Primary CWE-89: a single read-only SQL query over synthetic records."""
import sqlite3
ROUTE, METHOD, FIELDS = '/query', 'GET', ('name',)


def handle(p, state, change, reject):
    with sqlite3.connect('file:' + str(state / 'records.db') + '?mode=ro', uri=True) as db:
        db.execute('PRAGMA query_only=ON')
        # INTENTIONAL CWE-89: HTTP name is concatenated into SQL syntax.
        query = "SELECT label FROM records WHERE designated=0 AND name='" + p['name'] + "'"
        rows = db.execute(query).fetchall()
    return {'records': [r[0] for r in rows]}, 'application/json'
