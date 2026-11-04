"""Corrected CWE-20: required integer range 0..100, both bounds enforced."""
ROUTE, METHOD, FIELDS = '/level', 'POST', ('level', 'csrf')


def handle(p, state, change, reject):
    raw = p['level']
    if not raw.isascii() or not raw.isdecimal() or len(raw) > 3:
        raise reject()
    value = int(raw)
    if value > 100:
        raise reject()
    change(value)
    return {'level': value}, 'application/json'
