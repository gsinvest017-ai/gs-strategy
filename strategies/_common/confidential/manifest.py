"""Immutable inputs for the confidential broker; never a legacy-cache format.

Only the trusted broker supplies code fingerprints, owner, recipient and image
after authentication/policy checks. User-submitted hashes are not evidence.
The identity includes private strategy fingerprints and belongs inside the
encrypted result. This module establishes input identity, not financial validity.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path, PurePosixPath
import platform
import re
from typing import Mapping


MAX_SOURCE_BYTES = 64 * 1024
MAX_DATA_BYTES = 8 * 1024 * 1024
MAX_CONFIG_BYTES = 256 * 1024
_HASH = re.compile(r'[a-f0-9]{64}')
_IMAGE = re.compile(r'(?:sha256:|[A-Za-z0-9][A-Za-z0-9._/:~-]*@sha256:)[a-f0-9]{64}')


class ManifestError(ValueError):
    """Input cannot be represented by the immutable execution contract."""


def _validate(value, *, allow_floats=False, depth=0):
    if depth > 64:
        raise ManifestError('JSON nesting exceeds limit')
    kind = type(value)
    if kind in (str, int, bool):
        if kind is str:
            try:
                value.encode('utf-8')
            except UnicodeError as exc:
                raise ManifestError('valid UTF-8 strings required') from exc
        return
    if kind is float and allow_floats and math.isfinite(value):
        return
    if kind is list:
        for item in value:
            _validate(item, allow_floats=allow_floats, depth=depth + 1)
        return
    if kind is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise ManifestError('JSON object keys must be strings')
            _validate(key, depth=depth + 1)
            _validate(item, allow_floats=allow_floats, depth=depth + 1)
        return
    raise ManifestError('unsupported JSON type; metadata numbers must be integers or decimal strings')


def canonical_json(value) -> bytes:
    """Canonical metadata JSON: no floats, nulls, duplicate keys or custom types.

    Decimal quantities (costs, prices in config) must be explicit strings.
    UTF-8 is preserved exactly; no Unicode normalization is silently applied.
    """
    _validate(value)
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'),
                          ensure_ascii=False, allow_nan=False).encode('utf-8')
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ManifestError('invalid canonical JSON') from exc


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ManifestError('duplicate JSON object key')
        result[key] = value
    return result


def _constant(_):
    raise ManifestError('nonfinite JSON number')


def parse_json(data: bytes, *, allow_floats=False):
    """Strict UTF-8 JSON; callers remain responsible for their schema and size."""
    if type(data) is not bytes:
        raise ManifestError('immutable bytes required')
    try:
        value = json.loads(data.decode('utf-8'), object_pairs_hook=_pairs, parse_constant=_constant)
        _validate(value, allow_floats=allow_floats)
        return value
    except (ValueError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, ManifestError):
            raise
        raise ManifestError('invalid UTF-8 JSON') from exc


def sha256(data: bytes) -> str:
    if type(data) is not bytes:
        raise ManifestError('immutable bytes required')
    return hashlib.sha256(data).hexdigest()


def _digest(label, data):
    return sha256(label.encode('ascii') + b'\x00' + data)


def _hash(value):
    if type(value) is not str or not _HASH.fullmatch(value):
        raise ManifestError('lowercase SHA-256 hexadecimal digest required')


@dataclass(frozen=True)
class FrozenRun:
    source_utf8_bytes: bytes
    data_json_bytes: bytes
    config_json_bytes: bytes
    identity_json_bytes: bytes

    def __post_init__(self):
        for value, limit in ((self.source_utf8_bytes, MAX_SOURCE_BYTES),
                             (self.data_json_bytes, MAX_DATA_BYTES),
                             (self.config_json_bytes, MAX_CONFIG_BYTES),
                             (self.identity_json_bytes, MAX_CONFIG_BYTES)):
            if type(value) is not bytes or not 0 < len(value) <= limit:
                raise ManifestError('immutable input exceeds size limit or is empty')
        try:
            self.source_utf8_bytes.decode('utf-8')
        except UnicodeError as exc:
            raise ManifestError('strategy must be UTF-8') from exc
        if type(parse_json(self.data_json_bytes, allow_floats=True)) not in (dict, list):
            raise ManifestError('data must be a JSON object or array')
        config = parse_json(self.config_json_bytes)
        identity = parse_json(self.identity_json_bytes)
        if type(config) is not dict or type(identity) is not dict:
            raise ManifestError('config and identity must be JSON objects')
        if canonical_json(config) != self.config_json_bytes or canonical_json(identity) != self.identity_json_bytes:
            raise ManifestError('config and identity must use canonical encoding')
        expected = {'schema', 'source_sha256', 'data_sha256', 'config_sha256',
                    'engine_sha256', 'worker_sha256', 'image', 'owner', 'recipient_fingerprint', 'seed'}
        if set(identity) != expected or identity['schema'] != 'straty-frozen-run/1':
            raise ManifestError('unsupported immutable execution identity')
        for field in ('source_sha256', 'data_sha256', 'config_sha256', 'engine_sha256',
                      'worker_sha256', 'recipient_fingerprint'):
            _hash(identity[field])
        if type(identity['owner']) is not str or not identity['owner'] or len(identity['owner']) > 1024:
            raise ManifestError('stable owner subject required')
        if type(identity['seed']) is not int or not 0 <= identity['seed'] < 2**64:
            raise ManifestError('seed must be an unsigned 64-bit integer')
        if type(identity['image']) is not str or not _IMAGE.fullmatch(identity['image']):
            raise ManifestError('immutable image digest required')
        for field, data in (('source_sha256', self.source_utf8_bytes),
                            ('data_sha256', self.data_json_bytes), ('config_sha256', self.config_json_bytes)):
            if identity[field] != sha256(data):
                raise ManifestError('input content does not match identity')

    @property
    def source(self):
        return self.source_utf8_bytes.decode('utf-8')

    @property
    def data(self):
        return parse_json(self.data_json_bytes, allow_floats=True)

    @property
    def config(self):
        return parse_json(self.config_json_bytes)

    @property
    def identity(self):
        return parse_json(self.identity_json_bytes)

    @property
    def identity_sha256(self):
        return _digest('straty-frozen-run/1', self.identity_json_bytes)


def freeze_run(*, source: str, data: bytes, config: dict, owner: str,
               recipient_fingerprint: str, image: str, seed: int,
               engine_sha256: str, worker_sha256: str) -> FrozenRun:
    """Freeze once at the trusted broker boundary. Execute only these bytes.

    Code hashes MUST be measured by trusted broker code, never copied from an
    uploaded job. No paths are retained, and no original file is reopened here.
    Data keeps its original bytes; equivalent but differently encoded data has
    a different identity. Metadata is canonicalized for stable identity.
    """
    if type(source) is not str or type(config) is not dict or type(data) is not bytes:
        raise ManifestError('source string, immutable data bytes and config object required')
    try:
        source_bytes = source.encode('utf-8')
    except UnicodeError as exc:
        raise ManifestError('strategy must be UTF-8') from exc
    if not 0 < len(source_bytes) <= MAX_SOURCE_BYTES or not 0 < len(data) <= MAX_DATA_BYTES:
        raise ManifestError('input exceeds size limit or is empty')
    config_bytes = canonical_json(config)
    identity = {'schema': 'straty-frozen-run/1', 'source_sha256': sha256(source_bytes),
                'data_sha256': sha256(data), 'config_sha256': sha256(config_bytes),
                'engine_sha256': engine_sha256, 'worker_sha256': worker_sha256,
                'image': image, 'owner': owner, 'recipient_fingerprint': recipient_fingerprint, 'seed': seed}
    return FrozenRun(source_bytes, data, config_bytes, canonical_json(identity))


def fingerprint_files(files: Mapping[str, bytes], metadata: dict | None = None) -> str:
    """Domain-separated digest of named file bytes and trusted runtime metadata."""
    if not files or type(metadata if metadata is not None else {}) is not dict:
        raise ManifestError('nonempty files and metadata object required')
    hashes = {}
    for name, content in files.items():
        if type(name) is not str or not name or '\\' in name:
            raise ManifestError('normalized relative POSIX file name required')
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or path.as_posix() != name or ':' in name:
            raise ManifestError('normalized relative POSIX file name required')
        hashes[name] = sha256(content)
    payload = {'files': hashes, 'runtime': metadata if metadata is not None else {}}
    return _digest('straty-trusted-files/1', canonical_json(payload))


def trusted_package_fingerprint(package_root, image: str) -> str:
    """Measure every Python source plus actual broker runtime versions.

    The broker measures before AND after execution and rejects changes. This
    helper does not itself claim that code could not change between readings.
    The approved image digest binds worker Python/dependencies separately.
    """
    if type(image) is not str or not _IMAGE.fullmatch(image):
        raise ManifestError('immutable image digest required')
    root = Path(package_root).resolve()
    files = {}
    # rglob does not descend through directory symlinks. Reject them explicitly
    # rather than silently omit importable Python sources from the fingerprint.
    if any(path.is_symlink() for path in root.rglob('*')):
        raise ManifestError('trusted package must not contain symlinks')
    for path in sorted(root.rglob('*.py')):
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ManifestError('trusted package source must remain inside package root')
        files[path.relative_to(root).as_posix()] = path.read_bytes()
    return fingerprint_files(files, {'python_implementation': platform.python_implementation(),
                                    'python_version': platform.python_version(),
                                    'cryptography_version': version('cryptography'), 'image': image})
