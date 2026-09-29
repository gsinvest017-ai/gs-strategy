"""Offline synthetic futures bundle for integration tests (never production data).

The TEJ calendar package queries its holiday endpoint on import. Tests supply
an empty *post-2023* holiday fixture; all test sessions precede 2023 and use the
package's published static calendar. Zipline assets, writers, readers, event
loop, commissions, orders, fills, and accounting are all real.
Run this fixture serially: the vendor's official calendar CSV cache is shared
within the Python environment and is restored after import.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def import_zipline_offline():
    import tejapi
    import os
    previous_env = {key: os.environ.get(key) for key in ("TEJAPI_BASE", "TEJAPI_KEY")}
    os.environ["TEJAPI_BASE"] = "http://127.0.0.1:1"
    os.environ["TEJAPI_KEY"] = ""
    original = tejapi.fastget

    def calendar_fixture(table, **kwargs):
        if table != 'TWN/TRADEDAY_TWSE':
            raise RuntimeError('offline fixture forbids external data access')
        return pd.DataFrame({'zdate': pd.Series([], dtype='datetime64[ns]')})

    # TejToolAPI has an official CSV cache; prime and restore it for import.
    import importlib.util
    from pathlib import Path
    package = Path(importlib.util.find_spec('TejToolAPI').origin).parent
    cached = package / 'temp' / 'exchange_calendar.csv'
    cached.parent.mkdir(exist_ok=True)
    previous = cached.read_bytes() if cached.exists() else None
    pd.DataFrame({'zdate': pd.date_range('2016-01-01', '2035-01-01', freq='B')}).to_csv(cached, index=False)
    tejapi.fastget = calendar_fixture
    try:
        import zipline
        return zipline
    finally:
        tejapi.fastget = original
        for key, value in previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        if previous is not None:
            cached.write_bytes(previous)
        else:
            cached.unlink(missing_ok=True)


def register_fixture(name='graph_fixture'):
    import_zipline_offline()
    from zipline.data.bundles import register

    def ingest(environ, asset_db_writer, minute_bar_writer, daily_bar_writer,
               adjustment_writer, calendar, start_session, end_session, cache,
               show_progress, output_dir):
        sessions = calendar.sessions_in_range(start_session, end_session)
        metadata, frames = [], []
        sid = 0
        for root, multiplier in [('TX', 200), ('MTX', 50)]:
            for expiration in pd.date_range('2016-06-01', '2021-06-01', freq='QS-JUN'):
                expiry = calendar.date_to_session_label(expiration, direction='previous')
                listing = max(sessions[0], calendar.date_to_session_label(expiration - pd.DateOffset(months=18), direction='next'))
                last = min(sessions[-1], expiry)
                if last <= listing:
                    continue
                asset_sessions = calendar.sessions_in_range(listing, last)
                t = sessions.get_indexer(asset_sessions)
                close = 10000 * np.exp(.0003 * t + .1 * np.sin(t / 74) + .012 * np.sin(t / 3)) + sid * 2
                frame = pd.DataFrame({'open': close - 2, 'high': close + 8, 'low': close - 8,
                                      'close': close, 'volume': 100000, 'annotation': 1}, index=asset_sessions)
                metadata.append({'sid': sid, 'symbol': f'{root}{expiration:%Y%m}', 'root_symbol': root,
                                 'start_date': listing, 'end_date': last, 'notice_date': expiry,
                                 'expiration_date': expiry, 'auto_close_date': expiry,
                                 'exchange': 'TEJ_morning_future', 'multiplier': multiplier, 'tick_size': 1.})
                frames.append((sid, frame))
                sid += 1
        asset_db_writer.write(futures=pd.DataFrame(metadata).set_index('sid'),
                              exchanges=pd.DataFrame([{'exchange': 'TEJ_morning_future', 'canonical_name': 'TEJ_morning_future', 'country_code': 'TW'}]),
                              root_symbols=pd.DataFrame([{'root_symbol': r, 'root_symbol_id': i, 'exchange': 'TEJ_morning_future'} for i, r in enumerate(['TX', 'MTX'])]))
        daily_bar_writer.write(frames)
        adjustment_writer.write()

    register(name, ingest, calendar_name='TEJ_morning_future',
             start_session=pd.Timestamp('2016-01-04', tz='UTC'),
             end_session=pd.Timestamp('2020-12-31', tz='UTC'))
    return name

