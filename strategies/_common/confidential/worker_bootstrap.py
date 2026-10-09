"""Public container bootstrap. This module never receives broker secrets."""
import contextlib
import json
import sys


def main():
    protocol_out = sys.stdout
    max_bytes = int(sys.argv[1])

    def read():
        line = sys.stdin.buffer.readline(max_bytes + 1)
        if not line or len(line) > max_bytes or not line.endswith(b'\n'):
            raise ValueError('invalid frame')
        return json.loads(line)

    def emit(value):
        protocol_out.write(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')
        protocol_out.flush()

    setup = read()
    if set(setup) != {'source', 'nonce'}:
        raise ValueError('invalid setup')
    namespace = {'__name__': '__strategy__'}
    with contextlib.redirect_stdout(sys.stderr):
        exec(compile(setup['source'], '<strategy>', 'exec'), namespace)
    decide = namespace['decide']
    nonce = setup['nonce']
    emit({'nonce': nonce, 'ready': True})
    while True:
        frame = read()
        if set(frame) != {'nonce', 'seq', 'history', 'max_contracts'} or frame['nonce'] != nonce:
            raise ValueError('invalid request')
        with contextlib.redirect_stdout(sys.stderr):
            target = decide(frame['history'])
        if type(target) is not int or abs(target) > frame['max_contracts']:
            raise ValueError('invalid target')
        emit({'nonce': nonce, 'seq': frame['seq'], 'target': target})


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        # Do not print strategy source, exceptions, locals, or traceback.
        sys.exit(2)
