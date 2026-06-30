# Survey-First 決策報告：前沿量化交易理論×技術的 build/adopt 與 repo 落地

> 調查時點 2026-06。產出工具：`/survey-first`（四個平行研究 agent）。
> 環境前提：單人研究、Python/PyTorch、台灣期貨、zipline-tej（**日/分鐘 bar 回測，非 live L3 order book**）、
> RTX 5090（sm_120）、自架優先、私有 repo（GPL/AGPL 可用但標註）、**無量子硬體、無選擇權做市部位**。

---

## 一、總結論

| 主題 | 落地性 | 結論 | 對應 repo 動作 |
|---|---|---|---|
| 因果推斷 / Double ML 因子去擬合 | **高** | adopt 既有庫 + build 驗證 loop | 整併進 `gs-strategy`（`strategies/_common/causal/`） |
| Mamba/SSM + PatchTST 時序模型 | **中高** | adopt 模型庫 + build zipline 訊號橋 | 新建 `gs-ts-alpha` repo |
| Deep RL 執行 + concept drift/MLOps | **中**（執行重定義為排程） | adopt 工具 + build 三段 glue | drift/MLOps 進 `gs-strategy`；RL 執行新建 `gs-exec-rl` sandbox |
| 粗糙波動率 | **低 → 幾乎 skip** | 只 lift 一個 Hurst regime 特徵 | 一個 ~50 行 util 進 `gs-strategy` |
| Graph RAG 知識圖譜 | **中** | adopt LightRAG 疊在 gs-rag 上 | 整併進 `gs-rag`（Windows） |
| GNN / 流形組合優化 | **低 → skip（prod）** | 用 riskfolio/skfolio 古典法取代 | 整併進 `gs-strategy` |
| 量子 QAOA | **skip** | 用 CVXPY 古典 QP；無量子硬體零價值 | 不做 |

**一句話**：把資源集中在「因果去擬合 + PatchTST 訊號 + riskfolio 配置 + LightRAG 圖譜 + drift 熔斷」這五條；
rough vol、GNN covariance、QAOA 對「台灣期貨 + 單人 + 無選擇權/無量子硬體」落地性低，誠實跳過。

---

## 二、候選工具比較（adopt / partial / build）

### 群1 因果推斷 / Double ML（落地性高）

| 工具 | ~Stars | License | 覆蓋 | 結論 |
|---|---|---|---|---|
| DoubleML | ~0.65k | BSD-3 | DML 估計+信賴區間 | **adopt（主力）** |
| EconML | ~3k | MIT | DML + CATE（regime-conditional alpha） | adopt（補） |
| DoWhy | ~7k | MIT | DAG + refutation 反駁 API（去擬合閘門） | **adopt** |
| causal-learn | ~1.6k | MIT | DAG 自動發現（PC/GES/LiNGAM） | adopt |
| alphalens-reloaded | ~0.5k | Apache-2.0 | 因子 IC/event-study，zipline-tej 同血統 | **adopt（整合縫）** |
| mlfinlab（CPCV/DSR） | — | **已轉閉源付費** | — | **build（自寫，數百行）** |

### 群2 Mamba/SSM + PatchTST（落地性中高）

| 工具 | ~Stars | License | 覆蓋 | 結論 |
|---|---|---|---|---|
| thuml/Time-Series-Library | ~12.5k | MIT | 同庫含 Mamba+PatchTST+iTransformer | **adopt（model zoo）** |
| Nixtla/neuralforecast | ~4.2k | Apache-2.0 | 乾淨 `.fit/.predict` PatchTST | **adopt（DX 最佳）** |
| mamba-ssm | ~18.4k | Apache-2.0 | 官方 SSM kernel | partial（5090 要 from source 自編） |
| Chronos-2 / TimesFM-2 | ~5.5k/26k | Apache-2.0 | 預訓練 FM zero-shot baseline | partial（留意預訓練期與 OOS 重疊） |
| microsoft/qlib | ~44k | MIT | 完整量化平台 | adopt-conditional（只當架構參考） |

### 群3 Deep RL 執行 + concept drift / MLOps（落地性中，需重定義）

| 工具 | ~Stars | License | 覆蓋 | 結論 |
|---|---|---|---|---|
| Stable-Baselines3 | ~10.5k | MIT | PPO 引擎 | **adopt（主力）** |
| Gym-Trading-Env / gym-anytrading | ~0.6k/2.3k | MIT | OHLCV gym（吃 TEJ DataFrame） | **adopt** |
| river | ~5.4k | BSD-3 | ADWIN/KSWIN concept drift | **adopt（熔斷訊號源）** |
| hmmlearn / statsmodels Markov-switching / ruptures | ~3k/10k/2k | BSD | regime 偵測三視角 | **adopt** |
| MLflow + DVC | ~20k/14k | Apache-2.0 | 實驗追蹤 + 資料/模型版本 | **adopt（本機 SQLite，零 server）** |
| Feast（feature store） | ~6k | Apache-2.0 | — | **build-avoid（單人過度設計）** |
| ABIDES / mbt_gym | ~0.4k/0.2k | — | 合成 LOB 模擬 | partial（無 L3 資料，當學習用） |

### 群4 粗糙波動率 / GraphRAG / GNN / 量子（落地性分歧）

| 工具 | ~Stars | License | 結論 / 落地性 |
|---|---|---|---|
| LightRAG | ~37k | MIT | **adopt** — BGE-M3 原生、incremental insert、可疊 gs-rag。**中** |
| Microsoft GraphRAG | ~34k | MIT | partial（batch re-index 重） |
| riskfolio-lib | ~4.3k | BSD-3 | **adopt（配置主力）** — 26+ 風險測度。**高** |
| skfolio | ~1.9k | BSD-3 | **adopt（估計/驗證層）** — robust 共變異數 + walk-forward CV。**高** |
| PyTorch Geometric + geoopt/pymanopt | 23.9k/~1k | MIT/BSD | partial — 指數期貨板太小，shrinkage 更穩。**低→skip** |
| rough_bergomi / deepLearningVolatility | ~144/13 | MIT | partial 且多 stale — 無選擇權 → skip，只撿 Hurst 特徵 |
| qiskit-finance / qiskit-optimization | ~325/280 | Apache-2.0 | **skip** — IBM 不再官方支援、NISQ 無量子優勢 |

---

## 三、需自行實作的 gap 清單

1. **因果驗證 loop（最高價值 glue）**：`alphalens 因子 → causal-learn 建 DAG → DoubleML 估因果效應 → DoWhy refutation → pass/fail 判定`。
2. **回測過擬合統計（CPCV / Deflated & Probabilistic Sharpe / PBO）**：mlfinlab 已閉源，照 López de Prado 自寫。
3. **模型輸出 → zipline-tej 訊號橋**：每 rebalance 切窗 → 推論 → 映成分數 → 餵 `pipeline`/`handle_data`（~200–400 行）。
4. **purged + embargoed walk-forward**：預測庫預設會 look-ahead，財務防漏自寫。
5. **drift → hot-swap 熔斷編排**：river 給訊號，停策略 + 從 MLflow registry 載回 champion 的狀態機（~100 行）。
6. **LightRAG 落地層**：entity→ticker→訊號映射、point-in-time 版本化邊、zh-TW + TEJ code 抽取、信任閘延伸到圖譜 claim。

---

## 四、repo 落地對應

**整併進既有 repo**
- `gs-strategy` ← 因果驗證 loop（`_common/causal/`）、過擬合統計（`_common/validation/`）、riskfolio+skfolio 配置層（`_common/portfolio/`）、Hurst regime 特徵、river drift + regime（`_common/regime/`）。
- `gs-rag`（Windows `C:\Users\User\gs-rag`）← LightRAG 圖譜檢索器，疊在 BM25/BGE-M3+LanceDB 旁，共用 `Document` adapter 與 Ollama bge-m3/qwen3-coder:30b，半導體供應鏈 KB 當種子。
- `quant-research-skill` ← `/review-strategy` 加 CPCV/DSR/refutation 硬性檢查；`/quant-researcher` 回測加因果 gate。

**新建獨立 repo（依賴重、勿污染回測 env）**
- `gs-ts-alpha`：TSLib + neuralforecast + mamba-ssm（自編）+ Chronos/TimesFM baseline。獨立 conda env，用 parquet 把訊號交給 zipline-tej。
- `gs-exec-rl`：SB3 + Gym-Trading-Env + mbt_gym。執行重定義為「分鐘桶拆單排程 vs TWAP/VWAP」。

**不做**：rough_bergomi 校準棧、GNN 共變異數、所有量子 QAOA。

---

## 五、風險與注意事項

- **執行 RL 現實落差**：最優執行要 L3 order book，zipline-tej 只有日/分鐘 bar → 實際是「分鐘桶拆單排程」，別宣稱微秒滑價最小化。
- **授權地雷**：① mlfinlab 已閉源付費（勿 vendor，自寫 CPCV/DSR）；② alibi-detect 含 BSL-1.1（drift 改用 BSD 的 river/Frouros）。
- **已死/停更**：scikit-multiflow（→river）、fbm（→stochastic）、nano-graphrag、qiskit-finance（2024-02 凍結）、yuqinie98/PatchTST 與 lag-llama（research-grade，pin 死版本）。
- **5090 / sm_120 CUDA**：mamba-ssm 官方 wheel 不含 sm_120，需 `TORCH_CUDA_ARCH_LIST="12.0"` + CUDA 12.8 from source。先用純 PyTorch PatchTST 跑通，Mamba 當第二實驗。
- **統計陷阱**：DoWhy refutation 必做；預測庫預設 look-ahead；預訓練 FM 訓練期可能蓋 OOS；模型 zoo 易 spray → 務必 Bonferroni / Deflated Sharpe 校正。

---

## 六、執行順序（本報告對應的落地步驟）

1. `gs-strategy/_common/causal/`：DoubleML + DoWhy refutation，挑 `tsmom_tx_mtx` 的因子做「因果去擬合 PoC」。
2. 平行起 `gs-ts-alpha` 骨架：獨立 env 裝 neuralforecast，PatchTST 在 TX 分鐘 bar 跑通 → parquet 訊號橋。
3. 配置層 `_common/portfolio/`：riskfolio-lib（HRP/risk parity）+ skfolio（shrinkage 共變異數）。
4. `gs-rag` 疊 LightRAG：半導體供應鏈 KB 當種子，先質性驗證圖譜檢索。
5. CPCV / Deflated Sharpe 自寫後，塞進 `quant-research-skill` 的 `/review-strategy` 當硬性審查項。

---
*由 `/survey-first` 產生；本報告只負責選型，不含實作程式碼。實作骨架見 `strategies/_common/causal/`。*
