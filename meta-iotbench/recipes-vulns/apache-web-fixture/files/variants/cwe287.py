"""Primary CWE-287: login compares only the first eight proof characters."""
import hmac
ROUTE, METHOD, FIELDS = '/identity', 'GET', ()


def verify(supplied, expected):
    # INTENTIONAL CWE-287: the rest of the required password is never verified.
    return hmac.compare_digest(supplied[:8], expected[:8])


def handle(p, state, change, reject):
    return {'accepted_identity': 'admin'}, 'application/json'
