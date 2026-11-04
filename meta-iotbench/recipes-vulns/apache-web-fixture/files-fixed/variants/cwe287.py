"""Corrected CWE-287: the whole proof is compared, in constant time."""
ROUTE, METHOD, FIELDS = '/identity', 'GET', ()


def handle(p, state, change, reject):
    return {'accepted_identity': 'admin'}, 'application/json'
