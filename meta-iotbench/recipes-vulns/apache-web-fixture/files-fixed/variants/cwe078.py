"""Corrected CWE-78: the label is validated and written directly, no OS shell is involved."""
import re
ROUTE, METHOD, FIELDS = '/diagnostic', 'POST', ('label', 'csrf')


def handle(p, state, change, reject):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', p['label']):
        raise reject()
    (state / 'diagnostic.txt').write_text(p['label'])
    return {'ran': True}, 'application/json'
