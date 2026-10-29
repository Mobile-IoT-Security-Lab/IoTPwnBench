"""Primary CWE-20: required integer range 0..100; upper bound omitted."""
ROUTE, METHOD, FIELDS = '/level', 'POST', ('level', 'csrf')


def handle(p, state, change, reject):
    raw = p['level']
    if not raw.isascii() or not raw.isdecimal() or len(raw) > 3:
        raise reject()
    value = int(raw)
    # INTENTIONAL CWE-20: missing value <= 100, despite the documented contract.
    change(value)
    return {'level': value}, 'application/json'
