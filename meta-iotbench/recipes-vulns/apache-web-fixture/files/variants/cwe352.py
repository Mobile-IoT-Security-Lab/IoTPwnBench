"""Primary CWE-352: session + role checks retained; missing CSRF decision."""
ROUTE, METHOD, FIELDS = '/setting', 'POST', ('value',)
MISSING_CSRF = True


def handle(p, state, change, reject):
    if p['value'] not in ('ordinary', 'csrf-marker'):
        raise reject()
    # INTENTIONAL CWE-352: authenticated POST changes state without CSRF proof.
    change(p['value'])
    return {'value': p['value']}, 'application/json'
