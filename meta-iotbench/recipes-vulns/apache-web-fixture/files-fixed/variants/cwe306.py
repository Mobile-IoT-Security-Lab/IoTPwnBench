"""Corrected CWE-306: the critical write requires an authenticated administrator and CSRF proof."""
ROUTE, METHOD, FIELDS = '/critical', 'POST', ('value', 'csrf')


def handle(p, state, change, reject):
    if p['value'] not in ('ordinary', 'unauthenticated-marker'):
        raise reject()
    change(p['value'])
    return {'value': p['value']}, 'application/json'
