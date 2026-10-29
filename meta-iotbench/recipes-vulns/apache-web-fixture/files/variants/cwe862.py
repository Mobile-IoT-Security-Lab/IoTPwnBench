"""Primary CWE-862: identity + CSRF are checked; admin-only permission omitted."""
ROUTE, METHOD, FIELDS = '/admin-setting', 'POST', ('value', 'csrf')
MISSING_AUTHZ = True


def handle(p, state, change, reject):
    if p['value'] not in ('ordinary', 'reader-marker'):
        raise reject()
    # INTENTIONAL CWE-862: caller was authenticated, but its admin role was not checked.
    change(p['value'])
    return {'value': p['value']}, 'application/json'
