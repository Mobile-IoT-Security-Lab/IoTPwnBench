"""Primary CWE-306: benchmark setting requires identity, but has no role policy."""
ROUTE, METHOD, FIELDS = '/critical', 'POST', ('value',)
MISSING_AUTH = True


def handle(p, state, change, reject):
    if p['value'] not in ('ordinary', 'unauthenticated-marker'):
        raise reject()
    # INTENTIONAL CWE-306: no identity proof before this synthetic critical write.
    change(p['value'])
    return {'value': p['value']}, 'application/json'
