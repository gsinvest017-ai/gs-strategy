import base64

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from strategies._common.confidential import crypto
from strategies._common.confidential.manifest import canonical_json


@pytest.mark.parametrize('kind', ['ed25519', 'x25519'])
def test_raw_key_roundtrip(kind):
    private, public = crypto.generate_keypair(kind)
    assert len(base64.b64decode(private)) == len(base64.b64decode(public)) == 32
    assert crypto.public_key(private, kind) == public


def test_payload_roundtrip_randomized_and_canonical_aad():
    private, public = crypto.generate_keypair('x25519')
    payload = {'source': '機密', 'metrics': {'pnl': '123.45'}, 'positions': [0, 1, -1]}
    first = crypto.seal(payload, public, {'owner': 'alice', 'nonce': 'one'})
    second = crypto.seal(payload, public, {'nonce': 'one', 'owner': 'alice'})
    assert first != second
    assert crypto.open_envelope(first, private, {'nonce': 'one', 'owner': 'alice'}) == payload


@pytest.mark.parametrize('mutation', ['aad', 'recipient', 'ephemeral_public_key', 'nonce',
                                    'ciphertext', 'version', 'extra', 'missing'])
def test_envelope_tampering_rejected(mutation):
    private, public = crypto.generate_keypair('x25519')
    aad = {'request': 'one', 'owner': 'alice'}
    envelope = crypto.seal({'secret': 'never in errors'}, public, aad)
    if mutation == 'aad':
        aad['owner'] = 'bob'
    elif mutation == 'recipient':
        private, _ = crypto.generate_keypair('x25519')
    elif mutation == 'version':
        envelope['version'] = 'straty-envelope/2'
    elif mutation == 'extra':
        envelope['extra'] = 'ignored?'
    elif mutation == 'missing':
        del envelope['nonce']
    else:
        raw = bytearray(base64.b64decode(envelope[mutation]))
        raw[0] ^= 1
        envelope[mutation] = base64.b64encode(raw).decode()
    with pytest.raises(crypto.CryptoError) as caught:
        crypto.open_envelope(envelope, private, aad)
    assert 'never in errors' not in str(caught.value)


def test_signatures_bind_document_and_domain():
    private, public = crypto.generate_keypair('ed25519')
    document = {'header': {'owner': 'alice'}, 'envelope': {'ciphertext': 'opaque'}}
    signature = crypto.sign(document, private)
    assert crypto.verify(document, signature, public) is None
    other_private, other_public = crypto.generate_keypair('ed25519')
    with pytest.raises(crypto.CryptoError):
        crypto.verify(document, signature, other_public)
    naked = Ed25519PrivateKey.from_private_bytes(base64.b64decode(private)).sign(canonical_json(document))
    with pytest.raises(crypto.CryptoError):
        crypto.verify(document, base64.b64encode(naked).decode(), public)
    document['header']['owner'] = 'bob'
    with pytest.raises(crypto.CryptoError):
        crypto.verify(document, signature, public)


@pytest.mark.parametrize('bad', ['', '!', 'é', 'AA==', 'A' * 45, 4, None, 'A' * 44 + '\n'])
def test_bad_keys_have_bounded_uniform_errors(bad):
    with pytest.raises(crypto.CryptoError):
        crypto.public_key(bad, 'ed25519')
    with pytest.raises(crypto.CryptoError):
        crypto.seal({}, bad, {})


def test_reject_low_order_x25519():
    with pytest.raises(crypto.CryptoError):
        crypto.seal({}, base64.b64encode(bytes(32)).decode(), {})


@pytest.mark.parametrize('bad', [None, [], {'x': 1.5}, {'x': None}, {'x': float('nan')}, {1: 'x'}])
def test_documents_share_manifest_strict_canonicalization(bad):
    private, _ = crypto.generate_keypair('ed25519')
    _, recipient = crypto.generate_keypair('x25519')
    with pytest.raises(crypto.CryptoError):
        crypto.sign(bad, private)
    with pytest.raises(crypto.CryptoError):
        crypto.seal(bad, recipient, {})
    with pytest.raises(crypto.CryptoError):
        crypto.seal({}, recipient, bad)


def test_bounds_apply_before_decryption_and_signing(monkeypatch):
    private, public = crypto.generate_keypair('x25519')
    envelope = crypto.seal({'data': 'a' * 100}, public, {})
    monkeypatch.setattr(crypto, 'MAX_PAYLOAD_BYTES', 32)
    with pytest.raises(crypto.CryptoError):
        crypto.open_envelope(envelope, private, {})
    with pytest.raises(crypto.CryptoError):
        crypto.seal({'data': 'a' * 100}, public, {})
    monkeypatch.setattr(crypto, 'MAX_AAD_BYTES', 8)
    with pytest.raises(crypto.CryptoError):
        crypto.seal({}, public, {'request': 'a' * 20})
    monkeypatch.setattr(crypto, 'MAX_DOCUMENT_BYTES', 8)
    signing, _ = crypto.generate_keypair('ed25519')
    with pytest.raises(crypto.CryptoError):
        crypto.sign({'request': 'a' * 20}, signing)


def test_unknown_key_kind_is_rejected():
    with pytest.raises(crypto.CryptoError):
        crypto.generate_keypair('rsa')
    with pytest.raises(crypto.CryptoError):
        crypto.public_key('', 'rsa')


def test_noncanonical_base64_rejected():
    private, public = crypto.generate_keypair('x25519')
    envelope = crypto.seal({}, public, {})
    envelope['nonce'] += '='
    with pytest.raises(crypto.CryptoError):
        crypto.open_envelope(envelope, private, {})
