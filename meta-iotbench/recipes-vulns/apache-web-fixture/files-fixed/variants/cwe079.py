"""Corrected CWE-79: reflected input is HTML-encoded before it reaches the page."""
import html
ROUTE, METHOD, FIELDS = '/reflect', 'GET', ('message',)


def handle(p, state, change, reject):
    return ('<!doctype html><title>Synthetic reflection</title><main>' + html.escape(p['message']) + '</main>',
            'text/html')
