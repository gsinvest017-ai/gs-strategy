"""Hot-swappable chat-model calls with chain-of-thought capture.

Every provider speaks the OpenAI ``/chat/completions`` dialect, so swapping a
model is a registry entry (``models.yaml``), never a code change.  Responses are
normalised into ``{content, reasoning, usage}``:

* vLLM reasoning parsers return ``reasoning`` or ``reasoning_content``;
* models without a parser inline ``<think>...</think>`` (sometimes only the
  closing tag, because the chat template already opened it).

Each call is cached on disk by the full request identity, so a replay or a
re-run never re-queries the model and a backtest stays reproducible after the
provider changes.  API keys are read from an environment variable or a key
file and never appear in a cache entry, log, or error message.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from strategies._common.graph.core import GraphError, canonical
from . import pit

USER_AGENT = 'gs-strategy-graph/0.1'
_THINK = re.compile(r'<think>(.*?)</think>', re.S)
_FENCE = re.compile(r'^```[a-zA-Z]*\s*|\s*```$')


def normalize_message(message):
    content = message.get('content') or ''
    reasoning = message.get('reasoning_content') or message.get('reasoning') or ''
    inline = _THINK.findall(content)
    if inline:
        reasoning = (reasoning + '\n' + '\n'.join(inline)).strip()
        content = _THINK.sub('', content)
    elif '</think>' in content:
        head, _, content = content.partition('</think>')
        reasoning = (reasoning + '\n' + head.replace('<think>', '')).strip()
    return {'content': content.strip(), 'reasoning': reasoning.strip()}


def parse_json_object(content):
    """First JSON object in a reply (tolerates code fences and surrounding prose)."""
    text = _FENCE.sub('', content.strip())
    start = text.find('{')
    while start != -1:
        depth = 0
        for end in range(start, len(text)):
            if text[end] == '{':
                depth += 1
            elif text[end] == '}':
                depth -= 1
                if depth == 0:
                    try:
                        value = json.loads(text[start:end + 1])
                    except json.JSONDecodeError:
                        break
                    if isinstance(value, dict):
                        return value
                    break
        start = text.find('{', start + 1)
    return None


def _api_key(document):
    env = document.get('api_key_env')
    if env and os.environ.get(env):
        return os.environ[env].strip()
    for candidate in document.get('api_key_files') or []:
        path = Path(os.path.expanduser(candidate))
        try:
            if path.is_file():
                return path.read_text(encoding='utf-8').strip()
        except OSError:
            continue
    raise GraphError('LLM API key unavailable; set the configured environment variable or key file')


class FixtureProvider:
    """Deterministic stand-in: reads the 20-day momentum from the prompt's JSON."""

    def __init__(self, mode='momentum'):
        self.mode = mode

    def complete(self, messages, *, temperature, max_tokens):
        prompt = messages[-1]['content']
        if '"close"' in prompt and 'recall' in prompt:
            # No training data: the guess carries no information about the date.
            return {'content': '{"close": 20000}', 'reasoning': '沒有記憶，只能給一個與日期無關的猜測。', 'usage': {}}
        features = parse_json_object(prompt.split('FEATURES:', 1)[-1]) or {}
        momentum = float(features.get('ret_20d_pct') or 0.0)
        vol = max(float(features.get('vol_20d_pct') or 1.0), 1e-6)
        sign = 1 if self.mode == 'momentum' else -1
        direction = 'long' if sign * momentum > 0 else 'short' if sign * momentum < 0 else 'flat'
        confidence = round(min(0.95, 0.5 + abs(momentum) / (4 * vol)), 3)
        reasoning = (f'近 20 日報酬 {momentum:+.2f}%，20 日波動 {vol:.2f}%。'
                     f'動能/波動比 {momentum / vol:+.2f}，判斷方向為 {direction}。')
        content = json.dumps({'analysis': reasoning, 'direction': direction, 'confidence': confidence,
                              'rationale': '20 日動能方向'}, ensure_ascii=False)
        # Like an instruct model: no separate reasoning channel, analysis only.
        return {'content': content, 'reasoning': '', 'usage': {}}


class OpenAICompatibleProvider:
    def __init__(self, spec, document):
        # pit.registry() already rejects non-HTTP(S) base URLs; re-check at the call
        # site so no file:// or custom scheme can ever reach urllib.
        if urlsplit(spec['base_url']).scheme not in ('http', 'https'):
            raise GraphError('model base_url must be http(s)')
        self.base_url = spec['base_url'].rstrip('/')
        self.model = spec.get('api_model', '')
        self._document = document

    def complete(self, messages, *, temperature, max_tokens):
        body = json.dumps({'model': self.model, 'messages': messages, 'temperature': temperature,
                           'max_tokens': max_tokens}).encode()
        request = urllib.request.Request(self.base_url + '/chat/completions', data=body, headers={
            'Authorization': 'Bearer ' + _api_key(self._document), 'Content-Type': 'application/json',
            'User-Agent': USER_AGENT})
        last = None
        for attempt in range(3):
            try:
                # Scheme is restricted to http(s) in __init__ and in pit.registry().
                with urllib.request.urlopen(request, timeout=180) as response:  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
                    payload = json.load(response)
                message = payload['choices'][0]['message']
                return {**normalize_message(message), 'usage': payload.get('usage') or {}}
            except urllib.error.HTTPError as exc:
                last = f'HTTP {exc.code}'
                if exc.code < 500 and exc.code != 429:
                    break
            except (urllib.error.URLError, TimeoutError, OSError, KeyError, ValueError) as exc:
                last = type(exc).__name__
            time.sleep(2 * (attempt + 1))
        raise GraphError(f'LLM request failed ({last})')


def provider_for(model, path=pit.MODELS_PATH):
    document = pit.registry(path)
    spec = pit.model_spec(model, path)
    if spec['provider'] == 'fixture':
        return FixtureProvider(spec.get('fixture_mode', 'momentum'))
    return OpenAICompatibleProvider(spec, document)


class CallCache:
    def __init__(self, directory):
        self.directory = Path(directory)

    def key(self, model, spec, messages, temperature, max_tokens):
        identity = {'model': model, 'api_model': spec.get('api_model'), 'base_url': spec.get('base_url'),
                    'messages': messages, 'temperature': temperature, 'max_tokens': max_tokens}
        return hashlib.sha256(canonical(identity).encode()).hexdigest()

    def get(self, key):
        path = self.directory / (key + '.json')
        if path.is_file():
            return json.loads(path.read_text(encoding='utf-8'))
        return None

    def put(self, key, value):
        self.directory.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=self.directory, suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                json.dump(value, handle, ensure_ascii=False)
            os.replace(name, self.directory / (key + '.json'))
        finally:
            if os.path.exists(name):
                os.unlink(name)


def chat(model, messages, *, cache, temperature=0.0, max_tokens=1024, path=pit.MODELS_PATH):
    """One cached completion -> ``{content, reasoning, usage, cached, call_key}``."""
    spec = pit.model_spec(model, path)
    key = cache.key(model, spec, messages, temperature, max_tokens)
    hit = cache.get(key)
    if hit is not None:
        return {**hit, 'cached': True, 'call_key': key}
    result = provider_for(model, path).complete(messages, temperature=temperature, max_tokens=max_tokens)
    cache.put(key, result)
    return {**result, 'cached': False, 'call_key': key}
