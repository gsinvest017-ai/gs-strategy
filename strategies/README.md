# Taiwan Futures Strategies (Zipline-TEJ × TQuant-Lab)

從 `data/papers.db` 87 篇論文/報告中篩出 4 支可在台灣期貨市場執行的策略，
直接寫成 TQuant-Lab `tquant_future` bundle 可跑的回測程式碼。

## 策略一覽

| 目錄 | 對應論文 | 標的 | 訊號類型 | 期望年化 (paper原作) |
|---|---|---|---|---|
| `vgrsi_tx/` | arxiv 2605.01300 (Visibility Graphs RSI) | TX (台指期連續月) | 技術指標：可見圖 RSI | Sharpe 2.55-3.6 (DJI/EUR/XAU) |
| `cubic_momentum_tx/` | arxiv 2605.00854 (Periodic Bubbles) | TX | 三次方動量 + Hawkes 過熱 | 模型示意 |
| `tsmom_tx_mtx/` | wiley fut.70093 (Curve Momentum in China) + 業界共識 | TX/MTX | 12-1 月時序動量 + 波動目標 | Moskowitz et al. 經典 |
| `xsmom_stkfut_rmt/` | arxiv 2604.19107 (RMT Complexity Gap) + 個股期動量 | 個股期 universe | 橫斷面動量 + RMT regime overlay | regime-aware 變體 |

## 執行流程

```bash
# 1. 安裝依賴
pip install zipline-tej tejapi TejToolAPI alphalens-tej pyfolio-tej logbook ipywidgets pyyaml

# 2. 設定 TEJ API
export TEJAPI_KEY="<your-key>"
export TEJAPI_BASE="https://api.tej.com.tw"

# 3. ingest 期貨資料
export ticker="IR0001 IX0001"
export future="TX MTX"
export mdate="20180101 20260510"
zipline ingest -b tquant_future

# 4. 跑單一策略
cd strategies
python -m _common.runner \
    --strategy vgrsi_tx/strategy.py \
    --config   vgrsi_tx/config.yaml \
    --output   /tmp/vgrsi_tx_result.pkl
```

每個子目錄都有獨立 README 解釋假設、變數、限制。
