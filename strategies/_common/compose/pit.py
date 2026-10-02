"""Point-in-time (PIT) guards against look-ahead bias.

Two different clocks must agree before an LLM may see anything:

1. **Data knowledge time** -- a market row dated *d* is known at the close of
   *d*; a document is known from ``max(published, updated)`` (the stored text
   is the latest revision).  Unparseable dates are treated as unknown and the
   document is excluded (fail closed).
2. **Model knowledge cutoff** -- a decision date on or before
   ``cutoff + buffer`` business days is *contaminated*: the model may have
   trained on what happened next.  Prompts cannot fix this (asking a model to
   "ignore information after X" does not work, Lopez-Lira et al. 2025), so
   contaminated dates are never scored.
"""
from __future__ import annotations

from email.utils import parsedate_to_datetime
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd
import yaml

from strategies._common.graph.core import GraphError, digest

MODELS_PATH = Path(__file__).with_name('models.yaml')


@lru_cache(maxsize=8)
def _load(path, mtime):
    with open(path, encoding='utf-8') as handle:
        document = yaml.safe_load(handle)
    models = document.get('models') or {}
    for name, spec in models.items():
        if spec.get('provider') not in ('fixture', 'openai'):
            raise GraphError(f'model {name}: unsupported provider')
        if spec['provider'] == 'openai' and urlsplit(str(spec.get('base_url', ''))).scheme not in ('http', 'https'):
            raise GraphError(f'model {name}: base_url must be http(s)')
        spec['cutoff'] = str(pd.Timestamp(str(spec['cutoff'])).date())
    return document


def registry(path=MODELS_PATH):
    path = Path(path)
    return _load(str(path), path.stat().st_mtime_ns)


def model_names(path=MODELS_PATH):
    return list(registry(path)['models'])


def model_spec(name, path=MODELS_PATH):
    models = registry(path)['models']
    if name not in models:
        raise GraphError('unknown model')
    return dict(models[name])


def spec_digest(name, path=MODELS_PATH):
    """Identity of the selected model entry only, so adding other models keeps N."""
    return digest(model_spec(name, path))[:16]


def clean_start(cutoff, buffer_days):
    """First decision date that is strictly after ``cutoff + buffer`` business days."""
    return (pd.Timestamp(cutoff) + pd.offsets.BDay(int(buffer_days) + 1)).normalize()


def contaminated(dates, cutoff, buffer_days):
    start = clean_start(cutoff, buffer_days)
    index = pd.DatetimeIndex(pd.to_datetime(dates)).tz_localize(None)
    return pd.Series(index < start, index=index)


def parse_time(text):
    """ISO or RFC 2822 date -> naive Timestamp, or None when it cannot be trusted."""
    if text is None:
        return None
    text = str(text).strip()
    if not text:
        return None
    try:
        return pd.Timestamp(parsedate_to_datetime(text)).tz_convert(None) if ',' in text else _iso(text)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None


def _iso(text):
    value = pd.Timestamp(text)
    return value.tz_convert(None) if value.tzinfo else value


def knowledge_time(published, updated=None):
    times = [t for t in (parse_time(published), parse_time(updated)) if t is not None]
    if parse_time(published) is None:
        return None
    return max(times)


def visible(knowledge, decision_date, lag_days=1):
    """A document may enter the prompt for ``decision_date`` only if it was known ``lag_days`` before."""
    if knowledge is None:
        return False
    return knowledge.normalize() <= pd.Timestamp(decision_date).normalize() - pd.Timedelta(days=int(lag_days))
