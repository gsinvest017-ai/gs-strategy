from dataclasses import FrozenInstanceError, replace
import json

import pytest

from strategies._common.confidential.manifest import (
    MAX_DATA_BYTES, MAX_SOURCE_BYTES, ManifestError, canonical_json, fingerprint_files,
    freeze_run, parse_json, sha256, trusted_package_fingerprint,
)


IMAGE = 'sha256:' + 'a' * 64


def frozen(**overrides):
    args = {'source': 'def target(history):\n    return 0\n', 'data': b'[{"close":123.5}]',
            'config': {'cost': '0.25', 'timing': 'previous_close_next_open'},
            'owner': 'issuer|alice', 'recipient_fingerprint': 'b' * 64,
            'image': IMAGE, 'seed': 13, 'engine_sha256': 'c' * 64, 'worker_sha256': 'd' * 64}
    args.update(overrides)
    return freeze_run(**args)


def test_frozen_execution_inputs_survive_external_mutation(tmp_path):
    path = tmp_path / 'data.json'
    path.write_bytes(b'[{"close":123.5}]')
    config = {'cost': '0.25', 'nested': {'x': [1, 2]}}
    run = frozen(data=path.read_bytes(), config=config)
    identity = run.identity_sha256
    config['nested']['x'].append(99)
    path.write_bytes(b'[{"close":999}]')
    run.data[0]['close'] = 0
    run.config['nested']['x'].append(3)
    run.identity['owner'] = 'attacker'
    assert run.data == [{'close': 123.5}]
    assert run.config['nested']['x'] == [1, 2]
    assert run.identity['owner'] == 'issuer|alice'
    assert run.identity_sha256 == identity
    with pytest.raises(FrozenInstanceError):
        run.data_json_bytes = b'[]'
    with pytest.raises(ManifestError, match='does not match'):
        replace(run, data_json_bytes=b'[]')


@pytest.mark.parametrize('field,value', [
    ('source', 'def target(history):\n    return 1\n'), ('data', b'[{"close":124}]'),
    ('config', {'cost': '0.26'}), ('owner', 'issuer|bob'), ('recipient_fingerprint', 'e' * 64),
    ('image', 'sha256:' + 'f' * 64), ('seed', 14), ('engine_sha256', '1' * 64),
    ('worker_sha256', '2' * 64),
])
def test_every_material_input_changes_identity(field, value):
    assert frozen(**{field: value}).identity_sha256 != frozen().identity_sha256


def test_canonical_metadata_and_exact_data_bytes():
    assert canonical_json({'b': 2, 'a': '中文'}) == canonical_json({'a': '中文', 'b': 2})
    assert frozen(config={'a': 1, 'b': 2}).identity_sha256 == frozen(config={'b': 2, 'a': 1}).identity_sha256
    assert frozen(data=b'[1]').identity_sha256 != frozen(data=b'[ 1 ]').identity_sha256
    assert frozen().identity['data_sha256'] == sha256(b'[{"close":123.5}]')


@pytest.mark.parametrize('data', [b'{"x":1,"x":2}', b'{"nested":{"x":1,"x":2}}',
                                  b'[NaN]', b'[Infinity]', b'[-Infinity]', b'[1e999]',
                                  b'{"x":"\xff"}', b'123', b'"text"', b'null',
                                  b'[' * 66 + b'0' + b']' * 66])
def test_invalid_data_never_freezes(data):
    with pytest.raises(ManifestError):
        frozen(data=data)


@pytest.mark.parametrize('config', [{'cost': 0.25}, {'x': float('nan')}, {'x': None},
                                   {1: 'x'}, {'x': (1, 2)}, {'x': b'bytes'}])
def test_metadata_uses_strict_types(config):
    with pytest.raises(ManifestError):
        frozen(config=config)


@pytest.mark.parametrize('overrides', [
    {'source': 'a' * (MAX_SOURCE_BYTES + 1)}, {'source': '\ud800'}, {'source': ''},
    {'data': b' ' * (MAX_DATA_BYTES + 1)}, {'data': bytearray(b'[]')},
    {'image': 'python:latest'}, {'owner': ''}, {'recipient_fingerprint': 'invalid'},
    {'seed': True}, {'seed': -1}, {'seed': 2**64}, {'engine_sha256': 'C' * 64},
])
def test_limits_and_identity_fields(overrides):
    with pytest.raises(ManifestError):
        frozen(**overrides)


def test_file_manifest_binds_names_bytes_and_runtime():
    files = {'a.py': b'alpha', 'nested/b.py': b'beta'}
    baseline = fingerprint_files(files, {'python': '3.12'})
    assert baseline == fingerprint_files(dict(reversed(list(files.items()))), {'python': '3.12'})
    for changed, runtime in [({'a.py': b'changed', 'nested/b.py': b'beta'}, {'python': '3.12'}),
                             ({'renamed.py': b'alpha', 'nested/b.py': b'beta'}, {'python': '3.12'}),
                             (files, {'python': '3.13'})]:
        assert fingerprint_files(changed, runtime) != baseline
    with pytest.raises(ManifestError):
        fingerprint_files({'../escape.py': b'code'})


def test_package_fingerprint_includes_nested_sources_and_image(tmp_path):
    (tmp_path / '__init__.py').write_bytes(b'# init\n')
    sub = tmp_path / 'nested'
    sub.mkdir()
    module = sub / 'engine.py'
    module.write_bytes(b'# original\n')
    original = trusted_package_fingerprint(tmp_path, IMAGE)
    module.write_bytes(b'# changed\n')
    changed = trusted_package_fingerprint(tmp_path, IMAGE)
    assert original != changed
    assert changed != trusted_package_fingerprint(tmp_path, 'sha256:' + 'b' * 64)
    module.unlink()
    assert changed != trusted_package_fingerprint(tmp_path, IMAGE)


def test_constructor_cannot_bypass_content_binding():
    run = frozen()
    identity = run.identity
    identity['owner'] = ''
    with pytest.raises(ManifestError):
        replace(run, identity_json_bytes=canonical_json(identity))
    with pytest.raises(ManifestError, match='canonical'):
        replace(run, config_json_bytes=b'{ "cost": "0.25", "timing": "previous_close_next_open" }')
