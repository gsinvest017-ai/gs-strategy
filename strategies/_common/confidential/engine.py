"""Trusted daily futures accounting; the isolated strategy returns targets only.

Signals use history through i-1, orders fill at i open, and terminal liquidation
fills at the final close. Prices sent to the strategy are decimal strings.
This adapter validates bookkeeping and its input contract, not alpha, OOS,
exchange margin completeness, or the authenticity/availability of market data.
"""
from __future__ import annotations

from collections import deque
from datetime import date
from decimal import Decimal, InvalidOperation, Inexact, localcontext
import re

from .manifest import FrozenRun


class EngineError(ValueError):
    """Controlled rejection without embedding private strategy/data values."""


ZERO = Decimal(0)
ONE = Decimal(1)
_FIELDS = {'date', 'open', 'high', 'low', 'close'}
_CONFIG = {'adapter', 'point_value', 'commission_per_side', 'slippage_points',
           'initial_capital', 'margin_per_contract', 'max_contracts'}


def _decimal(value, *, positive=False, string_only=False):
    if type(value) not in ((str,) if string_only else (str, int, float)):
        raise EngineError('invalid numeric type')
    text = str(value)
    if len(text) > 128:
        raise EngineError('numeric precision exceeds adapter limit')
    try:
        number = Decimal(text)
    except InvalidOperation:
        raise EngineError('invalid decimal number') from None
    if (not number.is_finite() or number < 0 or (positive and number == 0)
            or len(number.as_tuple().digits) > 28
            or (number != 0 and abs(number.adjusted()) > 18)):
        raise EngineError('numeric value outside adapter limits')
    return number


def _string(number):
    # Avoid negative zero and exponent notation in portable result artifacts.
    return '0' if number == 0 else format(number, 'f')


def _validate(frozen):
    if type(frozen) is not FrozenRun:
        raise EngineError('immutable execution manifest required')
    frozen.__post_init__()
    config = frozen.config
    if set(config) != _CONFIG or config['adapter'] != 'daily-futures-next-open/1':
        raise EngineError('unsupported adapter configuration')
    if type(config['max_contracts']) is not int or not 1 <= config['max_contracts'] <= 1000:
        raise EngineError('invalid contract limit')
    values = {name: _decimal(config[name], positive=name in ('point_value', 'initial_capital', 'margin_per_contract'),
                             string_only=True)
              for name in _CONFIG - {'adapter', 'max_contracts'}}
    values['max_contracts'] = config['max_contracts']
    bars = frozen.data
    if type(bars) is not list or not 3 <= len(bars) <= 4096:
        raise EngineError('adapter requires 3 to 4096 daily bars')
    normalized = []
    previous = None
    for bar in bars:
        if type(bar) is not dict or set(bar) != _FIELDS:
            raise EngineError('invalid daily bar fields')
        text = bar['date']
        if type(text) is not str or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', text):
            raise EngineError('invalid daily date')
        try:
            day = date.fromisoformat(text)
        except ValueError:
            raise EngineError('invalid daily date') from None
        if previous is not None and day <= previous:
            raise EngineError('daily dates must be unique and strictly increasing')
        previous = day
        prices = {field: _decimal(bar[field], positive=True) for field in _FIELDS - {'date'}}
        if not (prices['low'] <= prices['open'] <= prices['high'] and
                prices['low'] <= prices['close'] <= prices['high']):
            raise EngineError('inconsistent daily OHLC')
        normalized.append({'date': text, **prices})
    return normalized, values


class _FIFO:
    """Independent realized trade accounting; no daily/equity inputs."""
    def __init__(self, point_value, side_cost):
        self.lots = deque()
        self.trades = []
        self.point_value = point_value
        self.side_cost = side_cost

    def fill(self, delta, price, day, event):
        if delta == 0:
            return
        direction = 1 if delta > 0 else -1
        remaining = abs(delta)
        while remaining and self.lots and self.lots[0]['direction'] != direction:
            lot = self.lots[0]
            quantity = min(remaining, lot['quantity'])
            gross = (price - lot['price']) * lot['direction'] * quantity * self.point_value
            entry_cost = self.side_cost * quantity
            exit_cost = self.side_cost * quantity
            self.trades.append({'entry_date': lot['date'], 'exit_date': day,
                                'entry_event': lot['event'], 'exit_event': event,
                                'side': 'long' if lot['direction'] == 1 else 'short', 'quantity': quantity,
                                'entry_price': _string(lot['price']), 'exit_price': _string(price),
                                'gross_pnl': _string(gross), 'entry_cost': _string(entry_cost),
                                'exit_cost': _string(exit_cost), 'pnl': _string(gross - entry_cost - exit_cost)})
            remaining -= quantity
            lot['quantity'] -= quantity
            if lot['quantity'] == 0:
                self.lots.popleft()
        if remaining:
            self.lots.append({'direction': direction, 'quantity': remaining, 'price': price, 'date': day, 'event': event})

    @property
    def position(self):
        return sum(lot['direction'] * lot['quantity'] for lot in self.lots)


def _verify(bars, config, daily, trades, equity_end):
    """Recompute both trade and daily paths independently from report totals."""
    equity = config['initial_capital']
    previous = 0
    daily_ok = True
    margin_ok = True
    fees = config['commission_per_side'] + config['slippage_points'] * config['point_value']
    for i, row in enumerate(daily, start=2):
        target = row['target_position']
        overnight = Decimal(previous) * (bars[i]['open'] - bars[i - 1]['close']) * config['point_value']
        intraday = Decimal(target) * (bars[i]['close'] - bars[i]['open']) * config['point_value']
        exit_quantity = abs(target) if i == len(bars) - 1 else 0
        cost = Decimal(abs(target - previous) + exit_quantity) * fees
        opening_cost = Decimal(abs(target - previous)) * fees
        margin_ok = margin_ok and Decimal(abs(target)) * config['margin_per_contract'] <= equity + overnight - opening_cost
        pnl = overnight + intraday - cost
        equity += pnl
        daily_ok = daily_ok and (row['previous_position'] == previous and Decimal(row['overnight_pnl']) == overnight
                                and Decimal(row['intraday_pnl']) == intraday and Decimal(row['total_cost']) == cost
                                and Decimal(row['pnl']) == pnl and Decimal(row['equity_close']) == equity)
        previous = 0 if i == len(bars) - 1 else target
    trade_ok = True
    trade_total = ZERO
    reported_trade_total = ZERO
    for trade in trades:
        direction = 1 if trade['side'] == 'long' else -1
        quantity = trade['quantity']
        gross = (Decimal(trade['exit_price']) - Decimal(trade['entry_price'])) * direction * quantity * config['point_value']
        cost = fees * quantity
        pnl = gross - cost * 2
        trade_ok = trade_ok and (Decimal(trade['gross_pnl']) == gross and Decimal(trade['entry_cost']) == cost
                                and Decimal(trade['exit_cost']) == cost and Decimal(trade['pnl']) == pnl)
        trade_total += pnl
        reported_trade_total += Decimal(trade['pnl'])
    return {'daily_components_match': daily_ok, 'daily_equity_reconciles': equity == equity_end,
            'trade_components_match': trade_ok, 'trade_pnl_reconciles': reported_trade_total == equity_end - config['initial_capital'],
            'recomputed_trade_pnl_reconciles': trade_total == equity_end - config['initial_capital'],
            'margin_precheck_passed': margin_ok, 'terminal_position_flat': previous == 0,
            'all_execution_days_recorded': len(daily) == len(bars) - 2}


def evaluate(frozen: FrozenRun, worker, job_nonce) -> dict:
    """Execute the fixed contract with no look-ahead access through this API."""
    bars, config = _validate(frozen)
    if type(job_nonce) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{16,128}', job_nonce):
        raise EngineError('opaque job nonce required')
    with localcontext() as context:
        context.prec = 80
        context.traps[Inexact] = True
        side_cost = config['commission_per_side'] + config['slippage_points'] * config['point_value']
        ledger = _FIFO(config['point_value'], side_cost)
        daily = []
        equity = config['initial_capital']
        previous = 0
        worker.start(frozen.source, job_nonce, seed=frozen.identity['seed'])
        for i in range(2, len(bars)):
            history = [{key: value if key == 'date' else _string(value) for key, value in bar.items()}
                       for bar in bars[:i]]
            target = worker.target(history=history, seq=i - 2, max_contracts=config['max_contracts'])
            if type(target) is not int or abs(target) > config['max_contracts']:
                raise EngineError('worker returned invalid target position')
            bar = bars[i]
            overnight = Decimal(previous) * (bar['open'] - bars[i - 1]['close']) * config['point_value']
            equity_open = equity + overnight
            change_cost = Decimal(abs(target - previous)) * side_cost
            if Decimal(abs(target)) * config['margin_per_contract'] > equity_open - change_cost:
                raise EngineError('target exceeds simplified opening margin capacity')
            ledger.fill(target - previous, bar['open'], bar['date'], 'open')
            if ledger.position != target:
                raise EngineError('FIFO target position mismatch')
            intraday = Decimal(target) * (bar['close'] - bar['open']) * config['point_value']
            terminal = i == len(bars) - 1
            exit_cost = Decimal(abs(target)) * side_cost if terminal else ZERO
            if terminal:
                ledger.fill(-target, bar['close'], bar['date'], 'terminal_close')
            pnl = overnight + intraday - change_cost - exit_cost
            equity += pnl
            daily.append({'date': bar['date'], 'previous_position': previous, 'target_position': target,
                          'closing_position': 0 if terminal else target, 'open': _string(bar['open']),
                          'close': _string(bar['close']), 'equity_open_before_cost': _string(equity_open),
                          'overnight_pnl': _string(overnight), 'intraday_pnl': _string(intraday),
                          'position_change_cost': _string(change_cost), 'terminal_exit_cost': _string(exit_cost),
                          'total_cost': _string(change_cost + exit_cost), 'pnl': _string(pnl), 'equity_close': _string(equity)})
            previous = 0 if terminal else target
        checks = _verify(bars, config, daily, ledger.trades, equity)
        checks['fifo_terminal_position_flat'] = ledger.position == 0
        checks['history_prefix_only'] = True
        checks['worker_targets_bounded_integers'] = True
        net = equity - config['initial_capital']
        # Division metrics may repeat; account balances above remain exact.
        with localcontext() as ratios:
            ratios.prec = 40
            ratios.traps[Inexact] = False
            total_return = net / config['initial_capital']
            days = (date.fromisoformat(bars[-1]['date']) - date.fromisoformat(bars[2]['date'])).days + 1
            years = Decimal(days) / Decimal('365.25')
            annual = total_return / years
            peak = config['initial_capital']
            mdd = ZERO
            for row in daily:
                balance = Decimal(row['equity_close'])
                peak = max(peak, balance)
                mdd = max(mdd, (peak - balance) / peak)
        metrics = {'initial_capital': _string(config['initial_capital']), 'equity_end': _string(equity),
                   'net_pnl': _string(net), 'total_return': _string(total_return),
                   'return_basis': 'net_pnl/initial_capital', 'annualized_return_simple': _string(annual),
                   'annualization_basis': 'total_return/calendar_years_no_compounding',
                   'calendar_days': days, 'calendar_years': _string(years), 'max_drawdown': _string(mdd),
                   'drawdown_basis': 'daily_close_equity_including_initial_capital',
                   'closed_trade_segments': len(ledger.trades), 'trading_days': len(daily),
                   'first_execution_date': bars[2]['date'], 'last_execution_date': bars[-1]['date']}
        return {'schema': 'straty-daily-futures-result/1', 'adapter': 'daily-futures-next-open/1',
                'metrics': metrics, 'trades': ledger.trades, 'daily': daily,
                'verification': {'status': 'passed' if all(checks.values()) else 'failed',
                                 'scope': ['accounting', 'streaming_contract'], 'checks': checks,
                                 'research_qualification': 'not_evaluated', 'oos': 'not_evaluated',
                                 'point_in_time_data_authenticity': 'not_evaluated',
                                 'fill_assumption': 'next_open_target_changes_final_close_liquidation',
                                 'execution_realism_limits': ['no_limit_or_volume_constraints', 'no_funding_or_roll_model',
                                                             'no_intraday_margin_or_forced_liquidation_model',
                                                             'cannot_detect_hardcoded_future_knowledge'],
                                 'margin_model': 'opening_capacity_after_transaction_cost_no_maintenance_or_liquidation_model'}}
