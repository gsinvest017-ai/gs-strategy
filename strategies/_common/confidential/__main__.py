"""Local-only confidential client CLI. Output paths must be explicitly selected."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from . import crypto
from .client import ClientError, pack_submission, verify_receipt, decrypt_result
from .manifest import MAX_CONFIG_BYTES, MAX_SOURCE_BYTES, canonical_json, parse_json, sha256


def _read(path, limit):
    with Path(path).open('rb') as handle:
        value = handle.read(limit + 1)
    if len(value) > limit:
        raise ClientError('input size limit exceeded')
    return value


def _exclusive(path, data):
    # O_EXCL also refuses existing symlinks. Private files use restrictive mode;
    # Windows ACLs remain the administrator/researcher endpoint's responsibility.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _key(path):
    return _read(path, 4096).decode('ascii').strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description='StratyUI confidential local client')
    commands = parser.add_subparsers(dest='command', required=True)
    generate = commands.add_parser('keygen')
    generate.add_argument('--kind', choices=('ed25519', 'x25519'), required=True)
    generate.add_argument('--private-out', type=Path, required=True)
    generate.add_argument('--public-out', type=Path, required=True)
    pack = commands.add_parser('pack')
    pack.add_argument('--spec', type=Path, required=True)
    pack.add_argument('--source', type=Path, required=True)
    pack.add_argument('--config', type=Path, required=True)
    pack.add_argument('--out', type=Path, required=True)
    for operation in ('verify', 'decrypt'):
        command = commands.add_parser(operation)
        command.add_argument('--result', type=Path, required=True)
        command.add_argument('--request', type=Path, required=True)
        command.add_argument('--broker-public', type=Path, required=True)
        command.add_argument('--broker-signing-key-id', required=True)
        command.add_argument('--subject', required=True)
        if operation == 'verify':
            command.add_argument('--recipient-public', type=Path, required=True)
        else:
            command.add_argument('--recipient-private', type=Path, required=True)
            command.add_argument('--out', type=Path, required=True,
                                 help='explicit plaintext result destination; never overwritten')
    args = parser.parse_args(argv)
    try:
        summary = {}
        if args.command == 'keygen':
            if (args.private_out.resolve() == args.public_out.resolve() or
                    args.private_out.exists() or args.public_out.exists()):
                raise ClientError('output already exists')
            private, public = crypto.generate_keypair(args.kind)
            _exclusive(args.private_out, (private + '\n').encode('ascii'))
            _exclusive(args.public_out, (public + '\n').encode('ascii'))
        elif args.command == 'pack':
            spec = parse_json(_read(args.spec, MAX_CONFIG_BYTES))
            if type(spec) is not dict:
                raise ClientError('spec must be an object')
            spec = dict(spec)
            for name in ('owner_private', 'broker_public', 'recipient_public'):
                key_path = Path(spec.pop(name + '_path'))
                if not key_path.is_absolute():
                    key_path = args.spec.resolve().parent / key_path
                spec[name] = _key(key_path)
            spec.setdefault('submission_id', None)
            result = pack_submission(source=_read(args.source, MAX_SOURCE_BYTES).decode('utf-8'),
                                     config=parse_json(_read(args.config, MAX_CONFIG_BYTES)), **spec)
            _exclusive(args.out, canonical_json(result))
        else:
            bundle = parse_json(_read(args.result, 24 * 1024 * 1024))
            request = parse_json(_read(args.request, 2 * 1024 * 1024))
            if args.command == 'verify':
                receipt = verify_receipt(bundle, _key(args.broker_public), sha256(canonical_json(request)),
                                         args.subject, _key(args.recipient_public), args.broker_signing_key_id)
                summary = {key: receipt[key] for key in ('execution', 'verification', 'delivery', 'research_qualification')}
            else:
                payload = decrypt_result(bundle, _key(args.recipient_private), _key(args.broker_public),
                                         expected_request=request, expected_subject=args.subject,
                                         expected_broker_signing_key_id=args.broker_signing_key_id)
                _exclusive(args.out, canonical_json(payload))
        print(json.dumps({'status': 'complete', 'operation': args.command, **summary}))
        return 0
    except Exception:
        # Do not echo exception strings: malformed inputs may embed private data.
        print(json.dumps({'error': 'confidential client operation failed'}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
