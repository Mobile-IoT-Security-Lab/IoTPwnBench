"""Primary CWE-78: unsafe OS shell construction inside a disposable namespace."""
import subprocess
ROUTE, METHOD, FIELDS = '/diagnostic', 'POST', ('label', 'csrf')


def handle(p, state, change, reject):
    # INTENTIONAL CWE-78: label crosses into OS shell syntax.
    subprocess.run("printf '%s' " + p['label'] + ' > diagnostic.txt', shell=True,
                   cwd=str(state), timeout=2, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   env={'PATH': '/bin', 'HOME': '/state'})
    return {'ran': True}, 'application/json'
