"""Corrected CWE-22: the resolved path must stay inside the allowed directory."""
ROUTE, METHOD, FIELDS = '/file', 'GET', ('file',)


def handle(p, state, change, reject):
    if p['file'].startswith('/'):
        raise reject()
    base = (state / 'allowed').resolve()
    path = (base / p['file']).resolve()
    if base not in path.parents:
        raise reject()
    return {'content': path.read_text()}, 'application/json'
