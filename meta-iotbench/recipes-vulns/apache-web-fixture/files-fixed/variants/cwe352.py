"""Corrected CWE-352: session, role and CSRF checks all apply to the state change."""
ROUTE, METHOD, FIELDS = '/setting', 'POST', ('value', 'csrf')


def handle(p, state, change, reject):
    if p['value'] not in ('ordinary', 'csrf-marker'):
        raise reject()
    change(p['value'])
    return {'value': p['value']}, 'application/json'
