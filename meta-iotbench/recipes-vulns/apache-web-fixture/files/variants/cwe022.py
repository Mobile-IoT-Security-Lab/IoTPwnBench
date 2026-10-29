"""Primary CWE-22: filesystem containment omitted at the allowed-directory boundary."""
ROUTE, METHOD, FIELDS = '/file', 'GET', ('file',)


def handle(p, state, change, reject):
    if p['file'].startswith('/'):
        raise reject()
    # INTENTIONAL CWE-22: ../ escapes allowed/ into the synthetic sentinel directory.
    path = state / 'allowed' / p['file']
    return {'content': path.read_text()}, 'application/json'
