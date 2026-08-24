---
type: progress
updated: 2026-05-10
repos: [gs-strategy]
owner: gsinvest017-kevin
---

# 從 87 篇 paper 篩出可在台灣期貨市場執行的策略 — 進度紀錄

**Session**: `f3349183-1543-4def-9ec5-6b3782f8b1d2`
**起始日期**: 2026-05-10
**目標框架**: Zipline-TEJ × TQuant-Lab (`tquant_future` bundle)
**目標商品**: 台指期 (TX)、小型台指 (MTX)、個股期 (FFF/DFF/JFF/KFF/HAF/...)

---

## 1. 篩選原則

對 `data/papers.db` 中 87 篇 metadata 採用以下 hard filter：

| 拒絕原因 | 篇數 (約) |
|---|---|
| 需要 tick / 高頻 / order book 資料 (TQ 只給日頻) | ~12 |
| 需要 DeFi / on-chain / Polymarket / 加密貨幣特定資料 | ~10 |
| 純理論 / 推導 / 不含可交易規則 | ~12 |
| 純美國 / G5 監理或政治事件特定 | ~8 |
| 選擇權定價、債券造市、商品種類無台灣對應 | ~15 |
| 抽象 abstract 過於空泛、僅 JFM EarlyView 占位 | ~24 |
| **總拒絕** | **~81** |

通過的策略候選（深度檢視 abstract 後判斷）：

| # | Source ID | Title | 為何適用台股期貨 |
|---|---|---|---|
| 1 | arxiv 2605.01300 | Visibility graphs can make money in financial markets (VGRSI) | 純日頻 OHLCV，已在 DJI30/EUR-USD/XAU-USD 跑出 Sharpe 2.55-3.6；TX 同為日頻 index futures |
| 2 | arxiv 2605.00854 | Dynamics of Periodic Bubbles and Crashes (Cubic Momentum) | 提供 cubic 動量 + Hawkes-like 過熱閥值的明確規則；單資產可實作 |
| 3 | wiley fut.70093 + 業界共識 | Curve Momentum in China (時序動量代表) | 時序動量 (TSMOM) 12-1 月格式對 TX/MTX 經典；JFM 同期實證亞洲市場 |
| 4 | arxiv 2604.19107 + 2604.16773 | RMT Complexity Gap regime filter + 個股期 cross-sectional momentum | 用 RMT gap 當 regime overlay，配合個股期橫斷面動量；TQ 已提供 `get_stock_futures_universe` |

最終實作 4 支策略。

---

## 2. 被剔除的代表性策略 (與原因)

- **arxiv 2605.05089 Spot-Perpetual Basis**: DeFi 永續合約，無對應商品。
- **arxiv 2605.04004 OHLCV Intraday Falsification**: 結論 = 無 edge，作為 negative result 不適合直接實作。
- **arxiv 2605.00459, 2605.00864 Polymarket**: 仰賴 Polymarket 限價簿資料。
- **arxiv 2604.26747 LLM Crypto Factors**: 加密貨幣專用 + 需要 LLM agent 框架。
- **arxiv 2604.19604 Put-Call Parity Carry Gap**: SPX/RUT options 限定。
- **arxiv 2604.13260 FinBERT Earnings Calls**: S&P500 transcripts 限定。
- **arxiv 2604.17327 MarketSenseAI Multi-Agent**: 需要 deployed LLM 系統。
- **AQR 全部 10 篇**: 多為 tax / asset-allocation 白皮書，無 paper-level alpha 規則。
- **NBER 4 篇**: 文化/法國公債/AlphaFold/AI portfolio (negative result)，皆不適合。
- **Fed FEDS 2 篇**: 央行獨立性史 + 房貸排隊理論。
- **JFM EarlyView**: abstract 為空，無法萃取規則 (僅可從題目推測)。

---

## 3. TQuant-Lab 框架關鍵 API (從官方 example notebook 萃取)

```python
from zipline.api import (
    continuous_future, future_symbol, symbol,
    set_commission, set_slippage, set_benchmark,
    schedule_function, date_rules, time_rules,
    order_target, order_target_percent, order,
    get_open_orders, cancel_order,
    attach_pipeline, pipeline_output, record,
)
from zipline.finance.commission import PerContract
from zipline.finance.slippage import FixedSlippage, FixedBasisPointsSlippage
from zipline import run_algorithm
from zipline.TQresearch.futures_package import (
    retail_long_short_ratio,        # 散戶多空比
    get_stock_futures_universe,     # 個股期 universe
)
```

關鍵點：
- **Bundle**: `tquant_future` (透過 env var `ticker`/`future`/`mdate` 控制 ingest 範圍)
- **Benchmark**: `symbol('IR0001')` = 加權報酬指數
- **Commission**: `PerContract(cost={'TX': 200, 'MTX': 100}, exchange_fee=0)` — TX 200 NTD/口
- **Slippage**: `FixedSlippage(spread=6.0)` — TX 6 點滑價 (1點 = 200 NTD)
- **Continuous future**: `continuous_future('TX', offset=0, roll='calendar', adjustment='add')`
- **Roll logic**: 每日 schedule，`held_contract.auto_close_date - today > 10 days` 不換月，否則 order_target → 0 並 order_target → 新月

---

## 4. 進度

| 步驟 | 狀態 |
|---|---|
| 記錄 session id | ✅ commit 60e8349 |
| 研究 TQuant-Lab API | ✅ |
| 篩選 87 篇 paper | ✅ |
| 寫進度紀錄 (本文件) | ✅ |
| 建立 strategies/ 目錄與共用 utils | ✅ commit 97e20a1 |
| 撰寫 4 支策略 + config | ✅ |
| py_compile 自我驗證 | ✅ |
| numpy 數值自我驗證 (VGRSI / cubic / RMT) | ✅ tests/test_strategy_math.py |
| 各階段 git commit | 🟡 進行中 |

---

## 5. 策略檔案規劃

```
strategies/
├── _common/
│   ├── __init__.py
│   ├── futures_setup.py        # 共用 commission/slippage/roll helper
│   └── runner.py               # run_algorithm wrapper、讀 config.yaml
├── vgrsi_tx/                   # arxiv 2605.01300
│   ├── strategy.py
│   ├── config.yaml
│   └── README.md
├── cubic_momentum_tx/          # arxiv 2605.00854
│   ├── strategy.py
│   ├── config.yaml
│   └── README.md
├── tsmom_tx_mtx/               # 古典時序動量
│   ├── strategy.py
│   ├── config.yaml
│   └── README.md
└── xsmom_stkfut_rmt/           # 個股期橫斷面動量 + RMT regime
    ├── strategy.py
    ├── config.yaml
    └── README.md
```

每個策略 README 含：對應 paper、假設、變數、回測指令。
每個 config.yaml 含：start/end/capital_base/universe/params/commission/slippage。

---

## 6. 跑回測前的環境前置 (使用者實機端)

```bash
# 1. 安裝 TQuant-Lab (需要 TEJ API key)
pip install zipline-tej tejapi TejToolAPI alphalens-tej pyfolio-tej logbook ipywidgets

# 2. 設 TEJ API key
export TEJAPI_KEY="<your-key>"
export TEJAPI_BASE="https://api.tej.com.tw"

# 3. ingest 期貨資料
export ticker="IR0001 IX0001"   # 加權指數 + 加權報酬指數
export future="TX MTX"           # 大台 + 小台
export mdate="20180101 20260510"
zipline ingest -b tquant_future

# 4. 跑策略
cd strategies/vgrsi_tx
python strategy.py --config config.yaml
```

`xsmom_stkfut_rmt` 額外需要 `get_stock_futures_universe` 取得個股期清單，再把 ticker/future env 補進來重新 ingest。

---

## 6.1 自我驗證結果

`tests/test_strategy_math.py` (跑 `/tmp/venv/bin/python tests/test_strategy_math.py`)：

- **VGRSI**: 嚴格遞增收盤 → 100.00；嚴格遞減 → 0.00；持平 → 50.00 ✅
- **Cubic signal**: f(0,1.5)=0；f(1.5,1.5)=1 (peak)；f(3.0,1.5)<0 (cubic flip) ✅
- **RMT complexity gap**: 1-factor 退化 collapse 時 gap≈0；IID 50 資產 gap≈+0.06 ✅

`py_compile` + `ast` 結構檢查 (4 支策略皆有 initialize/handle_data，
4 個 config.yaml 皆含 start/end/capital_base/bundle/calendar/params) ✅

## 7. 已知限制與後續 TODO

- 無法實機 ingest 跑回測 (sandbox 沒有 TEJ key)；策略檔僅做語法驗證
- TX/MTX 換月 logic 採 `roll='calendar'` (TQuant-Lab 預設)；若改 `roll='volume'` 需手動覆寫
- 滑價 6 點為示例值，實際視交易量與時段調整
- `xsmom_stkfut_rmt` 策略的 RMT 訊號需要至少 60 個流動性夠的個股期才有意義；上市初期可能 universe 太小
- 個股期到期日不一致，計算 cross-sectional momentum 時要對齊 continuous future 而非單一合約
