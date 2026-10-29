"""Primary CWE-77: local grammar = command (';' command)*.
Commands: SHOW <ASCII label> | MARK. No OS shell or subprocess is used.
"""
ROUTE, METHOD, FIELDS = '/command', 'POST', ('label', 'csrf')


def interpret(program, state, reject):
    result = []
    for command in program.split(';'):
        command = command.strip()
        if command.startswith('SHOW ') and command[5:].isascii() and command[5:].isalnum():
            result.append(command[5:])
        elif command == 'MARK':
            (state / 'interpreter.marker').write_text('application-command-marker\n')
        else:
            raise reject()
    return result


def handle(p, state, change, reject):
    # INTENTIONAL CWE-77: one label becomes multiple interpreter commands.
    return {'shown': interpret('SHOW ' + p['label'], state, reject)}, 'application/json'
