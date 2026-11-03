"""Corrected CWE-89: a single read-only SQL query with a bound parameter."""
import sqlite3
ROUTE, METHOD, FIELDS = '/query', 'GET', ('name',)


def handle(p, state, change, reject):
    with sqlite3.connect('file:' + str(state / 'records.db') + '?mode=ro', uri=True) as db:
        db.execute('PRAGMA query_only=ON')
        rows = db.execute('SELECT label FROM records WHERE designated=0 AND name=?', (p['name'],)).fetchall()
    return {'records': [r[0] for r in rows]}, 'application/json'
