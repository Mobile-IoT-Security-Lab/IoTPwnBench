"""Primary CWE-79: reflected input in HTML text; harmless DOM marker test."""
ROUTE, METHOD, FIELDS = '/reflect', 'GET', ('message',)


def handle(p, state, change, reject):
    # INTENTIONAL CWE-79: missing HTML text output encoding.
    return '<!doctype html><title>Synthetic reflection</title><main>' + p['message'] + '</main>', 'text/html'
