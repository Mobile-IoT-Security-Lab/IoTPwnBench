"""Corrected CWE-862: identity, CSRF and the admin-only permission are all checked."""
ROUTE, METHOD, FIELDS = '/admin-setting', 'POST', ('value', 'csrf')


def handle(p, state, change, reject):
    if p['value'] not in ('ordinary', 'reader-marker'):
        raise reject()
    change(p['value'])
    return {'value': p['value']}, 'application/json'
