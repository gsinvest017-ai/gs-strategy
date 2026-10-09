import copy
from datetime import date, timedelta
from decimal import Decimal
import json

import pytest

from strategies._common.confidential.engine import EngineError, evaluate
from strategies._common.confidential.manifest import canonical_json, freeze_run


CONFIG = {'adapter': 'daily-futures-next-open/1', 'point_value': '1', 'commission_per_side': '0',
          'slippage_points': '0', 'initial_capital': '10000', 'margin_per_contract': '100', 'max_contracts': 10}


def bars(*prices):
    result = []
    for i, (opening, closing) in enumerate(prices):
        result.append({'date': (date(2024, 1, 1) + timedelta(days=i)).isoformat(),
                       'open': str(opening), 'high': str(max(opening, closing)),
                       'low': str(min(opening, closing)), 'close': str(closing)})
    return result


def freeze(data, **config):
    return freeze_run(source='def decide(history): return 0', data=json.dumps(data).encode(),
                      config={**CONFIG, **config}, owner='issuer|alice', recipient_fingerprint='a' * 64,
                      image='sha256:' + 'b' * 64, seed=42, engine_sha256='c' * 64, worker_sha256='d' * 64)


class Worker:
    def __init__(self, targets, *, mutate=False):
        self.targets = iter(targets)
        self.histories = []
        self.started = False
        self.mutate = mutate

    def start(self, source, nonce, seed):
        self.started = True
        self.seed = seed

    def target(self, history, seq, max_contracts):
        assert seq == len(self.histories)
        self.histories.append(copy.deepcopy(history))
        if self.mutate:
            history[-1]['close'] = '9999999'
        return next(self.targets)


def run(data, targets, **config):
    return evaluate(freeze(data, **config), Worker(targets), 'a' * 32)


def assert_accounts(result, expected):
    assert Decimal(result['metrics']['net_pnl']) == Decimal(expected)
    assert sum(Decimal(t['pnl']) for t in result['trades']) == Decimal(expected)
    assert sum(Decimal(d['pnl']) for d in result['daily']) == Decimal(expected)
    assert result['verification']['status'] == 'passed'
    assert all(result['verification']['checks'].values())
    assert result['verification']['research_qualification'] == 'not_evaluated'
    # Entire result is accepted by the strict encrypted-artifact serializer.
    canonical_json(result)


def test_first_loss_counts_in_drawdown_and_exit_gets_overnight_pnl():
    data = bars((100, 100), (100, 100), (100, 90), (95, 105))
    result = run(data, [1, 0], point_value='50')
    assert_accounts(result, '-250')
    assert Decimal(result['metrics']['max_drawdown']) == Decimal('0.05')
    assert Decimal(result['daily'][0]['intraday_pnl']) == -500
    assert Decimal(result['daily'][1]['overnight_pnl']) == 250
    assert Decimal(result['daily'][1]['intraday_pnl']) == 0
    assert result['trades'][0]['exit_event'] == 'open'
    assert result['metrics']['drawdown_basis'] == 'daily_close_equity_including_initial_capital'


@pytest.mark.parametrize('target,opening,closing,expected', [(1, 100, 110, '396'), (-2, 100, 90, '792')])
def test_long_short_final_close_and_both_side_costs(target, opening, closing, expected):
    result = run(bars((100, 100), (100, 100), (opening, closing)), [target],
                 point_value='50', commission_per_side='2', slippage_points='1')
    assert_accounts(result, expected)
    assert result['daily'][-1]['closing_position'] == 0
    assert result['trades'][-1]['exit_event'] == 'terminal_close'
    assert Decimal(result['daily'][-1]['terminal_exit_cost']) == abs(target) * 52


def test_reversal_closes_then_opens_with_full_turnover_costs():
    result = run(bars((100, 100), (100, 100), (100, 102), (105, 100)), [2, -1],
                 point_value='50', commission_per_side='2', slippage_points='1')
    assert_accounts(result, '438')
    assert [t['side'] for t in result['trades']] == ['long', 'short']
    assert [t['quantity'] for t in result['trades']] == [2, 1]
    assert [Decimal(t['pnl']) for t in result['trades']] == [Decimal(292), Decimal(146)]
    assert Decimal(result['daily'][1]['position_change_cost']) == 3 * 52


def test_fifo_scale_in_and_out_has_independent_entry_prices():
    result = run(bars((100, 100), (100, 100), (100, 101), (102, 103), (104, 105), (106, 107)),
                 [1, 3, 1, 0], commission_per_side='1')
    assert_accounts(result, '4')
    assert [t['entry_price'] for t in result['trades']] == ['100', '102', '102']
    assert [t['exit_price'] for t in result['trades']] == ['104', '104', '106']
    assert [t['quantity'] for t in result['trades']] == [1, 1, 1]


def test_short_gap_exit_and_zero_position():
    data = bars((100, 100), (100, 100), (100, 100), (120, 90))
    result = run(data, [-1, 0])
    assert_accounts(result, '-20')
    assert Decimal(result['daily'][1]['overnight_pnl']) == -20
    assert_accounts(run(data, [0, 0]), '0')


def test_history_is_prefix_only_and_worker_mutation_cannot_change_accounting():
    data = bars((10, 11), (12, 13), (14, 15), (16, 17))
    worker = Worker([1, 1], mutate=True)
    result = evaluate(freeze(data), worker, 'a' * 32)
    assert_accounts(result, '3')
    assert worker.seed == 42
    assert worker.histories[0] == data[:2]
    assert worker.histories[1] == data[:3]
    assert all(history[-1]['date'] < result['daily'][i]['date'] for i, history in enumerate(worker.histories))


def test_future_mutation_preserves_earlier_signals_and_daily_results():
    class Momentum(Worker):
        def target(self, history, seq, max_contracts):
            self.histories.append(copy.deepcopy(history))
            return 1 if Decimal(history[-1]['close']) > Decimal(history[-2]['close']) else 0
    original = bars((100, 100), (100, 101), (102, 103), (104, 105), (106, 107))
    changed = copy.deepcopy(original)
    changed[-1].update(open='999', high='1000', low='998', close='1000')
    one = evaluate(freeze(original), Momentum([]), 'a' * 32)
    two = evaluate(freeze(changed), Momentum([]), 'a' * 32)
    assert one['daily'][:-1] == two['daily'][:-1]
    assert [row['target_position'] for row in one['daily']] == [row['target_position'] for row in two['daily']]


def test_annualization_is_simple_calendar_time():
    data = bars((100, 100), (100, 100), (100, 110), (110, 120))
    data[-1]['date'] = '2025-01-02'
    result = run(data, [1, 1], initial_capital='100')
    assert_accounts(result, '20')
    days = (date(2025, 1, 2) - date(2024, 1, 3)).days + 1
    assert result['metrics']['calendar_days'] == days
    expected = Decimal('0.2') * Decimal('365.25') / Decimal(days)
    assert abs(Decimal(result['metrics']['annualized_return_simple']) - expected) < Decimal('1e-25')


@pytest.mark.parametrize('target', [True, 1.0, '1', {'pnl': 999}, 11, -11])
def test_worker_cannot_supply_pnl_or_unbounded_positions(target):
    with pytest.raises(EngineError, match='invalid target'):
        run(bars((100, 100), (100, 100), (100, 101)), [target])


def test_margin_check_uses_opening_equity_including_gap():
    with pytest.raises(EngineError, match='margin'):
        run(bars((100, 100), (100, 100), (100, 100)), [2], initial_capital='1000', margin_per_contract='600')
    # A gap loss reduces opening capital before a same-sized target is approved.
    with pytest.raises(EngineError, match='margin'):
        run(bars((100, 100), (100, 100), (100, 100), (1, 2)), [1, 1],
            initial_capital='100', margin_per_contract='50')


def test_opening_cost_is_reserved_before_margin_check():
    with pytest.raises(EngineError, match='margin'):
        run(bars((100, 100), (100, 100), (100, 100)), [1], initial_capital='100',
            margin_per_contract='100', commission_per_side='1')
    # The final close releases the position; its exit fee does not require
    # maintaining the just-released contract margin.
    result = run(bars((100, 100), (100, 100), (100, 100)), [1], initial_capital='101',
                 margin_per_contract='100', commission_per_side='1')
    assert_accounts(result, '-2')


@pytest.mark.parametrize('change', [
    lambda b: b[1].update(date=b[0]['date']),
    lambda b: b[1].update(date='2024-02-30'),
    lambda b: b[1].update(date='2024-1-02'),
    lambda b: b[1].update(open=True),
    lambda b: b[1].update(open='NaN'),
    lambda b: b[1].update(open='Infinity'),
    lambda b: b[1].update(low='0'),
    lambda b: b[1].update(high='99'),
    lambda b: b[1].update(extra='unknown'),
    lambda b: b.pop(),
])
def test_invalid_data_is_rejected_before_worker_start(change):
    data = bars((100, 100), (100, 100), (100, 101))
    change(data)
    worker = Worker([1])
    with pytest.raises(EngineError):
        evaluate(freeze(data), worker, 'a' * 32)
    assert not worker.started


@pytest.mark.parametrize('override', [{'adapter': 'unrecognized'}, {'max_contracts': True}, {'max_contracts': 1001},
                                     {'max_contracts': 0}, {'point_value': '0'}, {'commission_per_side': '-1'},
                                     {'slippage_points': '-0.1'}, {'initial_capital': '0'}, {'margin_per_contract': '0'},
                                     {'commission_per_side': 1}, {'unapproved': 'field'}])
def test_invalid_config_is_rejected_before_worker_start(override):
    worker = Worker([1])
    with pytest.raises(EngineError):
        evaluate(freeze(bars((100, 100), (100, 100), (100, 101)), **override), worker, 'a' * 32)
    assert not worker.started


def test_independent_reconciliation_detects_corrupted_trade_report(monkeypatch):
    from strategies._common.confidential import engine
    original = engine._FIFO.fill
    def corrupt(self, *args, **kwargs):
        original(self, *args, **kwargs)
        if self.trades:
            self.trades[-1]['pnl'] = '999999'
    monkeypatch.setattr(engine._FIFO, 'fill', corrupt)
    result = run(bars((100, 100), (100, 100), (100, 101)), [1])
    assert result['verification']['status'] == 'failed'
    assert result['verification']['checks']['trade_components_match'] is False
