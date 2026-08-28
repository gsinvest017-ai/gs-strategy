# 價量技術分析的數學規格

> 來源：2026-08-28「交易之夜」聽課筆記 + 本人補充。
> 目的：把技術分析的口語敘述翻譯成**可驗證、可計算、可證偽**的數學敘述，
> 並指出哪些地方文獻已經有答案、哪些地方我在猜、哪些地方口語說法其實是錯的。
>
> 閱讀方式：每節都是「筆記原話 → 形式化 → 可計算定義 → 落地模組 → 誠實的但書」。
> **但書那一段才是重點。** 一個沒有但書的量化敘述通常是錯的。

---

## §0 記號與設定

固定一個過濾機率空間 $(\Omega, \mathcal{F}, (\mathcal{F}_t)_{t\ge 0}, \mathbb{P})$。

| 記號 | 意義 |
|---|---|
| $P_t$ | 價格（收盤，除權息還原） |
| $r_t = \log P_t - \log P_{t-1}$ | 對數報酬 |
| $V_t$ | 成交量（股數或口數） |
| $A_t = P_t V_t$ | 成交金額（turnover proxy） |
| $\mathcal{F}_t$ | 到 $t$ 收盤為止所有可得資訊 |
| $\mathcal{F}^{(m)}_t$ | 只用尺度 $m$（週K／日K／小時K）資訊生成的子過濾 |
| $W_t$ | 權益曲線；$M_t = \sup_{s\le t} W_s$ 為 running max |
| $d_t = 1 - W_t/M_t \in [0,1)$ | 當下回撤深度 |
| $L$ | 槓桿倍數 |

**貫穿全文的唯一硬規則（causality / PIT）**

> 任何在 $t$ 時刻要拿來下單的量 $X_t$，必須是 $\mathcal{F}_t$-可測；
> 任何用來做**標準化**的統計量（均值、標準差、分位數），必須是 $\mathcal{F}_{t-1}$-可測。

第二句常被忽略。把 $t$ 自己算進它自己的 z-score 分母，會系統性壓縮極端值、
讓「突破」訊號在回測中比實盤好看。這不是理論潔癖，是可量測的偏誤。
所有模組都寫了對應的 property test（見 §10）。

---

## §1 價量因子

### 1.1 筆記原話

> Blume, Easley, O'Hara 1994 / Tsang, Chang 2009 OBV / Excess trading volume 用於做空頭預測 /
> VWAP、TWAP、Volume breakout、Divergence

### 1.2 形式化：成交量是「訊號精度」的代理，不是「訊號方向」的代理

Blume–Easley–O'Hara (1994, *Journal of Finance*) 的核心結論值得用一句數學講清楚。
設市場中有一個關於資產價值的訊號 $S = \theta + \varepsilon$，$\varepsilon \sim N(0, 1/\tau)$，
$\tau$ 是**精度（precision）**。他們的結果是：

$$\text{價格 } P_t \text{ 攜帶 } \mathbb{E}[\theta \mid \cdot] \text{ 的資訊；成交量 } V_t \text{ 攜帶 } \tau \text{ 的資訊。}$$

也就是說，**價格告訴你市場相信什麼，成交量告訴你市場多相信它**。
這是價量分析唯一有嚴謹微觀結構基礎的一句話，其他大部分都是它的工程化推論。

直接的可操作推論：

$$\mathbb{E}[|r_{t+1}| \mid \mathcal{F}_t] \text{ 對 } V_t \text{ 敏感，而 } \mathbb{E}[r_{t+1} \mid \mathcal{F}_t] \text{ 未必。}$$

> **但書（重要）**：這解釋了為什麼「量能檢定」對**波動度**與**續航力**有預測力，
> 卻對**方向**幾乎沒有。很多價量策略的回測 Sharpe 來自它偷偷做多了波動度，
> 而不是它預測了方向。§5 的 Ljung–Box 對 $r_t$ 與對 $|r_t|$ 分開檢定，就是要把這兩件事拆開。

### 1.3 OBV 的正確數學身分：帶號成交量的部分和

$$\mathrm{OBV}_t = \sum_{s \le t} \operatorname{sign}(P_s - P_{s-1})\, V_s, \qquad \operatorname{sign}(0) := 0$$

這個定義讓 OBV 立刻變成可檢定的對象。在「量不含方向資訊」的虛無假設下，
$\operatorname{sign}(\Delta P_s)$ 與 $V_s$ 獨立且前者平均為 0，於是

$$H_0:\quad \mathrm{OBV}_t \text{ 是一個 martingale（無漂移隨機遊走）。}$$

所以「OBV 背離」在數學上就是在問：**OBV 的漂移項是否顯著非零，且與價格漂移反號**。
這可以用 §5 的 variance ratio 或 Wald–Wolfowitz runs test 直接檢定，
不需要用肉眼在圖上找背離。

> **但書**：筆記寫的 "Tsang, Chang 2009 OBV" 這條引用**我無法查證**。
> 我沒有在記憶中找到對應的可靠文獻，也沒有在本機論文庫 `data/papers.db` 找到。
> 我不會替它編一個出處。要嘛請提供完整書目，要嘛就把 OBV 當作 1963 年 Granville
> 的原始構造 + 上面這個 martingale 檢定框架來用——後者本身就站得住腳，不需要靠那篇。

### 1.4 Excess volume（過量成交量）

筆記說「用於做空頭預測」。形式化：取 $v_t = \log(1+V_t)$（穩定變異數），

$$\mathrm{XV}_t = \frac{v_t - \mu_{t-1}}{\sigma_{t-1}}, \qquad
\mu_{t-1} = \frac{1}{w}\sum_{i=1}^{w} v_{t-i}, \quad
\sigma^2_{t-1} = \frac{1}{w-1}\sum_{i=1}^{w}(v_{t-i}-\mu_{t-1})^2$$

注意求和是 $i=1..w$，**不含 $t$ 自己**。這正是 §0 的第二句規則。

「空頭預測」的可檢定版本：

$$H_1:\quad \mathbb{E}[r_{t+h} \mid \mathrm{XV}_t > k,\ r_t < 0] < \mathbb{E}[r_{t+h}]$$

也就是**放量下跌**（而非單純放量）才是空方訊號。這個條件化很關鍵——
單獨的 $\mathrm{XV}_t > k$ 在多頭噴出時同樣成立，兩者相消後通常沒有淨效果。

### 1.5 VWAP / TWAP：兩個不同的測度

這兩個東西常被並列，但它們是對**不同測度**取的期望：

$$\mathrm{VWAP}_{[a,b]} = \frac{\int_a^b P_s \, dV_s}{\int_a^b dV_s} = \mathbb{E}^{\,\mathbb{Q}_V}[P], \qquad
\mathrm{TWAP}_{[a,b]} = \frac{1}{b-a}\int_a^b P_s\, ds = \mathbb{E}^{\,\mathbb{Q}_T}[P]$$

其中 $\mathbb{Q}_V$ 是以成交量為密度的測度（Radon–Nikodym 導數 $d\mathbb{Q}_V/ds \propto dV_s/ds$），
$\mathbb{Q}_T$ 是均勻測度。

這個觀點的用處：**VWAP − TWAP 的正負，直接告訴你量集中在價格區間的哪一側**。

$$\mathrm{VWAP} - \mathrm{TWAP} = \operatorname{Cov}^{\mathbb{Q}_T}\!\left(P_s, \frac{dV_s/ds}{\overline{dV/ds}}\right)$$

是價格與**相對成交強度**的共變數。大於 0 表示量堆在高價區（買方積極 / 出貨區），
小於 0 表示量堆在低價區。這比「收盤在 VWAP 之上」多帶了一階資訊。

> **但書**：日 K 只有 OHLC 時，TWAP 只能用 $(O+H+L+C)/4$ 近似，
> 這個近似的誤差在單邊趨勢日可以到數十 bps。模組裡把它命名為 proxy 並在 docstring 標明。

### 1.6 背離（Divergence）的無歧義定義

肉眼找背離不可重現。可計算定義：在窗口 $[t-w, t]$ 上，

$$\beta^P_t = \text{OLS slope of } P \text{ on time}, \qquad
\rho_t = \operatorname{Spearman}\big(P_{t-w:t},\ \mathrm{OBV}_{t-w:t}\big)$$

$$\text{Bearish divergence}_t := \mathbf{1}\{\beta^P_t > 0\} \cdot \mathbf{1}\{\rho_t < \rho^*\}$$

用 Spearman 而非 Pearson，是因為我們要的是**序關係**（形態）而非線性關係，
且對量的厚尾穩健。

**落地**：`strategies/_common/factors/volume.py`

---

## §2 因子標準化 SOP

### 2.1 筆記原話

> Quant 對交易量因子（以及其他特徵）都會做的 SOP：detrending/standardization → z-score

### 2.2 形式化：這是在做「條件矩正規化」

原始因子 $x_t$ 通常同時含有三種不想要的東西：
(a) 長期趨勢（成交量隨市值成長）、(b) 時變尺度（波動叢聚）、(c) 厚尾。
SOP 就是依序處理：

$$x_t \;\xrightarrow{\text{detrend}}\; \tilde{x}_t = x_t - g(t) \;\xrightarrow{\text{scale}}\; z_t = \frac{\tilde{x}_t - \mu_{t-1}}{\sigma_{t-1}} \;\xrightarrow{\text{winsorize}}\; \operatorname{clip}(z_t, \pm c)$$

三個選擇各自有代價，寫清楚：

| 步驟 | 常見選擇 | 代價 |
|---|---|---|
| detrend | 一階差分 / 對數差分 / 滾動 OLS 殘差 | 差分會放大高頻噪音；OLS 殘差需要窗口長度假設 |
| scale | z-score / rank / robust (MAD) | z-score 對離群值敏感；rank 丟失幅度資訊；MAD 在近常態下效率損失約 37% |
| winsorize | $c \in [3,5]$ | 過度 clip 會把「真正的極端事件」（正是你想抓的）壓平 |

**關鍵洞見**：如果你的策略要抓的就是尾部事件（爆量、跌停、處置股），
那 winsorize 會把訊號本身砍掉。此時應該用 rank 或直接用**指示函數**
$\mathbf{1}\{z_t > k\}$ 而不是連續值。

> **但書**：橫斷面標準化（同一天所有股票之間）與時序標準化（同一股票跨時間）
> 是**兩種完全不同的操作**，混用會產生看不見的偏誤。
> 橫斷面 z-score 天然免疫於市場層級的共同衝擊（它被減掉了），時序 z-score 不是。
> 選哪一個取決於你的策略是 market-neutral 還是 directional。

**落地**：`volume.standardize()` / `volume.detrend()`

---

## §3 多尺度訊號處理

### 3.1 筆記原話

> 傳統訊號分析：wavelet transform 偵測各個尺度形態學的 resonance。
> NN 方法：CNN（進階 GNN）。缺點：各種資料週期速度更新的非同步性。
> overfitting solution: combinatorial purged cross-validation

### 3.2 為什麼是 wavelet 而不是 Fourier

金融序列不是平穩的，Fourier 基底 $e^{i\omega t}$ 在時間上無限延展，
無法回答「這個週期成分**什麼時候**出現」。小波基底 $\psi_{j,k}(t) = 2^{-j/2}\psi(2^{-j}t - k)$
同時局部化於時間與尺度，正好對應交易者說的「哪個週期的形態在哪個時間發生」。

多解析度分析（MRA）給出正交分解

$$L^2(\mathbb{R}) = \mathcal{V}_J \oplus \bigoplus_{j=1}^{J} \mathcal{W}_j,
\qquad x_t = S_{J,t} + \sum_{j=1}^{J} D_{j,t}$$

$D_{j}$ 是尺度 $2^j$ 的細節（≈ 週期 $2^{j}$~$2^{j+1}$ 根 K 棒的成分），$S_J$ 是趨勢殘留。

### 3.3 必須用 MODWT，不能用 DWT

這是本節最重要的工程判斷，理由有三，全部對交易致命：

1. **平移不變性**。標準 DWT 有下採樣（decimation），輸入平移一根 K 棒，
   小波係數會**質變**而非平移。也就是說：同一段行情，你昨天跑跟今天跑會得到不同的形態判讀。
   MODWT（maximal overlap DWT，又稱 à trous / undecimated）沒有下採樣，
   $\mathrm{MODWT}(x_{\cdot - \tau}) = \mathrm{MODWT}(x)_{\cdot - \tau}$。
2. **樣本長度**。DWT 要求 $N = 2^J$；MODWT 對任意 $N$ 定義。
3. **能量守恆**。MODWT 滿足 $\sum_j \|W_j\|^2 + \|V_J\|^2 = \|x\|^2$，
   所以「各尺度能量佔比」是一個有意義的方差分解。

> **但書（本節最大的坑）**：教科書的 MODWT 用**循環邊界**，這在右端點是**非因果**的——
> $t$ 的係數用到了 $t+1, t+2, \dots$（繞回開頭）。
> 用它產生訊號＝直接前視。模組因此提供兩種模式：
> `mode='circular'`（能量守恆、可完美重構、**僅供研究診斷**）與
> `mode='causal'`（只往回看、暖機期為 NaN、**唯一可用於下單**）。
> 兩者數值不同，這是物理限制不是 bug。任何論文若報告了小波策略的績效卻沒說明邊界處理，
> 它的績效預設不可信。

### 3.4 跨尺度共振（resonance）

筆記講的「resonance」我形式化為**跨尺度方向一致性**：

$$R_t = \frac{\sum_{j \in \mathcal{J}} w_j \cdot \operatorname{sign}\big(W_{j,t}\big)}{\sum_{j \in \mathcal{J}} w_j}
\;\in [-1, 1], \qquad w_j = \frac{\|W_j\|^2}{\sum_{i}\|W_i\|^2}$$

$|R_t| \to 1$：所選尺度全部同向 → 共振。$R_t \approx 0$：尺度間互相打架。

權重取能量佔比，而不是均權，理由是：一個在該標的上幾乎沒有能量的尺度，
它的符號基本上是噪音的符號，不該與主導尺度等權投票。

### 3.5 非同步更新問題

筆記正確指出這是最大缺點。形式化：週 K、日 K、4H K 的資訊到達時間不同，
若直接把週 K 值 `ffill` 到日頻，會讓「本週還沒結束的週 K」洩漏到本週的日 K 訊號裡。

正確做法是 **as-of backward join on the coarse bar's CLOSE timestamp**：

$$X^{(W)}_t := X^{(W)}_{k}, \quad k = \max\{k' : \tau^{\text{close}}_{k'} \le t\}$$

其中 $\tau^{\text{close}}_{k}$ 是第 $k$ 根週 K 的**收盤**時刻，不是它的標籤時刻。
模組另外提供 `lag_bars=1`（預設）再延一根，作為對「收盤到可交易」延遲的保守處理。

> **但書**：這件事在 pandas 裡特別容易錯，因為 `resample('W')` 預設用**週期起點或終點作為 label**
> 取決於 `label=` 與 `closed=` 參數，而預設值在不同 pandas 版本間變過。
> 不要相信預設值，永遠顯式指定，並寫一個「週 K 值在該週收盤前不可見」的測試。

### 3.6 CNN / GNN 這條路

筆記提到用 CNN 吃跨尺度形態出熱力圖。這是可行的，但要說清楚它換到了什麼：

- CNN 把 §3.4 手工定義的 $R_t$ 換成**學出來的**跨尺度算子。
  好處：能抓到我沒想到的形態組合。壞處：參數量從 0 跳到 $10^5$，
  而 §8 會告訴你這在高槓桿下是致命的。
- **CPCV 是必要條件不是充分條件**。CPCV 解決的是「時序重疊標籤造成的洩漏」，
  它**不解決**「你試了 500 個模型然後報告最好那個」。後者要 §6 的 White/SPA。
  兩者正交，都要做。本 repo 的 CPCV 已在 `validation/cpcv.py`，
  White/SPA/StepM 是這次補上的 `validation/reality_check.py`。

**落地**：`strategies/_common/factors/multiscale.py`

---

## §4 中心思想：條件機率

### 4.1 筆記原話

> large-scale data as filter, small-scale data as executor。
> 用條件機率解釋 P(trading signal in small-scale morphology | large-scale morphology)。
> 將交易者經驗法則量化：週 K 選方向 → 日 K 選位置 → 4hr/1hr K 選 signal

### 4.2 形式化：巢狀過濾上的鏈式分解

令 $\mathcal{F}^{(W)}_t \subset \mathcal{F}^{(D)}_t \subset \mathcal{F}^{(H)}_t$
（週 ⊂ 日 ⊂ 小時，資訊由粗到細遞增）。定義三個事件：

- $A$ = 週 K 給出的方向正確（$\operatorname{sign}$ 對）
- $B$ = 日 K 給出的進場位置好（例如回檔到支撐而非追高）
- $C$ = 小時 K 給出的觸發時點好

則單筆交易獲利的機率作**鏈式分解**：

$$\mathbb{P}(\text{win}) = \underbrace{\mathbb{P}(A)}_{\text{週K：選方向}} \cdot \underbrace{\mathbb{P}(B \mid A)}_{\text{日K：選位置}} \cdot \underbrace{\mathbb{P}(C \mid A, B)}_{\text{小時K：選訊號}}$$

這個式子把交易者的經驗法則寫成了一個**可分別估計、可分別檢定**的東西。
每一層都可以獨立問：這一層的條件化到底加了多少？

### 4.3 提升度（lift）與它的陷阱

第 $k$ 層的價值用**提升度**衡量：

$$\mathrm{Lift} = \frac{\mathbb{P}(\text{win} \mid \text{signal}, \text{filter})}{\mathbb{P}(\text{win} \mid \text{signal})}$$

$\mathrm{Lift} > 1$ 表示濾網有用。**但這是整份筆記裡我覺得最容易騙到人的地方**，
所以要把陷阱寫死在模組裡：

> **加濾網一定會提高勝率（在樣本內），因為它同時砍掉了樣本數。**
>
> 設無條件樣本 $n$、勝率 $p$；加濾網後 $n_c = n/10$、勝率 $p_c$。
> $p_c$ 的標準誤是 $\sqrt{p_c(1-p_c)/n_c}$，樣本砍 10 倍 → 標準誤放大 $\sqrt{10} \approx 3.16$ 倍。
> 一個看起來 lift = 1.4 的濾網，如果 $n_c = 25$，它的 95% Wilson 信賴區間
> 幾乎必然涵蓋 $p$，也就是**與「沒有濾網」統計上不可區分**。

因此模組的 `conditional_lift()` **強制**同時回傳 `n_cond`、Wilson CI、
兩比例檢定的 p 值，以及一個 `power_warning` 旗標。
**沒有附 $n_c$ 與 CI 的 lift 不是證據，是裝飾。**

### 4.4 三層濾網的樣本代價是相乘的

這是鏈式分解的直接推論，也是實務上最痛的一點：

$$n_{\text{final}} \approx n \cdot \mathbb{P}(A)\cdot \mathbb{P}(B\mid A) \cdot \mathbb{P}(C \mid A,B)$$

三層各留 1/3，最後只剩 $n/27$。10 年日資料（$n \approx 2400$）打完三層濾網
剩下不到 90 筆。用 90 筆去估計一個 Sharpe，其標準誤約 $\sqrt{(1+\mathrm{SR}^2/2)/90} \approx 0.11$（年化後更大）。

**所以「週 K 選方向 → 日 K 選位置 → 小時 K 選訊號」在統計上要成立，
必須在更細的頻率上執行**（小時 K 的 $n$ 大 24 倍），或者跨標的做橫斷面 pooling
換取樣本數。單一標的的日頻三層濾網，本質上是無法驗證的。

**落地**：`multiscale.conditional_lift()` / `multiscale.mtf_align()`

---

## §5 這個標的適合做技術分析嗎？

### 5.1 筆記原話

> 在對投資標的套用技術分析形態學的量化策略之前，先判斷此標的是否適合做技術分析

這是整份筆記裡**最有價值的一句**，而且是大多數人跳過的一步。形式化：

$$H_0:\quad (P_t) \text{ 是鞅（martingale）}, \quad \mathbb{E}[P_{t+1}\mid \mathcal{F}_t] = P_t$$

若無法拒絕 $H_0$，則**任何**只用 $\mathcal{F}_t$ 中價格資訊的策略，其期望超額報酬為零。
形態學再漂亮也沒有用；回測看到的邊際優勢就是選擇偏誤。

### 5.2 檢定組合

| 檢定 | 抓什麼 | 虛無下的值 |
|---|---|---|
| Variance Ratio $VR(q)$ (Lo–MacKinlay 1988) | 線性序列相關的**跨期結構** | 1 |
| Hurst 指數 $H$ (R/S, DFA) | 長記憶 | 0.5 |
| Permutation entropy (Bandt–Pompe 2002) | **序關係**上的決定性結構（非線性也抓得到） | 1 |
| Ljung–Box on $r_t$ | 方向的線性可預測性 | 不拒絕 |
| Ljung–Box on $\lvert r_t\rvert$ | 波動叢聚 | **幾乎必然拒絕** |
| Runs test | 符號序列的隨機性 | 不拒絕 |

Variance ratio 是這組裡最有力的，因為它的**形狀**帶資訊：

$$VR(q) = \frac{\operatorname{Var}(r_t + \dots + r_{t-q+1})}{q\operatorname{Var}(r_t)}
= 1 + 2\sum_{k=1}^{q-1}\left(1 - \frac{k}{q}\right)\rho_k$$

$VR(q) > 1$ ⟹ 正自相關主導 ⟹ **趨勢型**策略有機會。
$VR(q) < 1$ ⟹ 負自相關主導 ⟹ **均值回歸型**策略有機會。
$VR(q) \approx 1\ \forall q$ ⟹ 別浪費時間。

> **但書（必須大聲說）**：$\lvert r_t \rvert$ 的 Ljung–Box 在**任何**金融資產上都會拒絕，
> 因為波動叢聚是普世現象。把它當成「這個標的可以做技術分析」的證據是**錯的**——
> 它只證明了波動可預測，不證明方向可預測。
> 模組把兩者分開回報，就是為了堵住這個最常見的誤讀。

### 5.3 誠實的定位

模組提供的 `ta_suitability()` 給一個 0–100 分。這個分數**沒有抽樣分布**，
它是一個篩選啟發式，不是檢定。真正的證據是各成分的 p 值。
而且這些檢定彼此不獨立，所以總分也不是一個做過多重檢定校正的東西。
「suitable」是必要條件，不是充分條件。模組的 `caveats` 欄位強制非空。

**落地**：`strategies/_common/validation/tradability.py`

---

## §6 多重檢定：你到底試了幾次？

### 6.1 筆記原話

> 使用 White's reality check (using statistical bootstrap) 以及進階方法
> Hansen's SPA test / Stepwise multiple testing

### 6.2 問題陳述

你試了 $M$ 個策略（或同一策略的 $M$ 組參數），報告最好的那個。
即使**全部都沒有 alpha**，最好那個的 $t$ 統計量也會很好看：

$$\mathbb{E}\left[\max_{k \le M} t_k\right] \approx \sqrt{2\log M} \quad (M \text{ 個獨立標準常態})$$

$M = 100$ 時這是 $3.03$。你的「$t = 3$，顯著！」在試了 100 組參數之後，
**正好就是純噪音的期望值**。

### 6.3 三個修正，由粗到細

**White's Reality Check (2000)**
$$V = \max_k \sqrt{T}\,\bar{f}_k, \qquad
V^*_b = \max_k \sqrt{T}\left(\bar{f}^*_{b,k} - \bar{f}_k\right), \qquad
p = \frac{1}{B}\sum_b \mathbf{1}\{V^*_b > V\}$$
$\bar f_k$ 是策略 $k$ 相對基準的績效差。用 stationary bootstrap (Politis–Romano 1994)
重抽以保留序列相關。$H_0: \max_k \mathbb{E}[f_k] \le 0$。

**Hansen's SPA (2005)** —— 對 RC 的兩點改良：
1. **學生化**：除以 $\hat\omega_k$，讓不同波動度的策略可比。
2. **重新置中只針對「還算好」的策略**：
   $$g_k = \bar f_k \cdot \mathbf{1}\left\{\bar f_k \ge -\sqrt{\tfrac{\hat\omega_k^2}{T}\,2\log\log T}\right\}$$
   為什麼重要：RC 的 $\max$ 會被一堆**明顯很爛**的策略拖累（它們讓 bootstrap 分布右尾變胖），
   造成檢定力低下。把它們剔除，SPA 幾乎總是比 RC 更容易拒絕虛無。
   模組同時回傳 $p_l / p_c / p_u$ 三個版本，$p_u$ 就是 RC。

**Romano–Wolf StepM (2005)** —— 回答不同的問題：
RC/SPA 只告訴你「**是否至少有一個**策略有效」。StepM 逐步剔除，
在控制 FWER 的前提下告訴你**具體哪幾個**有效。做策略池篩選時要用這個。

### 6.4 與既有模組的分工

| 問題 | 工具 | 位置 |
|---|---|---|
| 時序標籤重疊造成的洩漏 | CPCV | `validation/cpcv.py`（既有） |
| 單一策略 Sharpe 的估計誤差 | PSR / DSR | `validation/sharpe.py`（既有） |
| IS 最佳者 OOS 崩潰的機率 | PBO | `validation/pbo.py`（既有） |
| **試了 M 個策略的資料窺探** | **White RC / SPA / StepM** | **`validation/reality_check.py`（本次新增）** |

四者互補，不可互相取代。DSR 需要一個誠實的 $M$；RC/SPA 直接吃整個 $M$ 維績效矩陣，
不需要你自己申報 $M$——這正是它比 DSR 難作弊的地方。

**落地**：`strategies/_common/validation/reality_check.py`

---

## §7 MDD 最佳化與槓桿

### 7.1 筆記原話

> Grossman-Zhou 1993 / Cvitanić, Karatzas 1995 / Fractional Kelly formula with drawdown constraint /
> Mean-max drawdown optimization / Magdon-Ismail, Atiya 2004 / CVaR / DRL reward design for MDD /
> 給定 MDD 之下對於槓桿比率的最佳化

### 7.2 回撤的尺度律（Magdon-Ismail & Atiya 2004）

對漂移 $\mu$、波動 $\sigma$ 的布朗運動，時間長度 $T$：

$$\mathbb{E}[\mathrm{MDD}] \sim
\begin{cases}
\sqrt{\pi/2}\;\sigma\sqrt{T} \approx 1.2533\,\sigma\sqrt{T} & \mu = 0 \quad \text{(閉式，精確)}\\[4pt]
\dfrac{\sigma^2}{2\mu}\log\!\left(\dfrac{2\mu^2 T}{\sigma^2}\right) & \mu > 0 \quad \text{(大 } T \text{ 漸近)}\\[4pt]
|\mu|\,T & \mu < 0 \quad \text{(漸近)}
\end{cases}$$

**這三行是本節最值得記住的東西**：

- 沒有 edge（$\mu=0$）：回撤以 $\sqrt{T}$ 成長。跑越久，回撤越深，**無上界**。
- 有 edge（$\mu>0$）：回撤只以 $\log T$ 成長。**幾乎有界**。
- 負 edge：線性歸零。

推論：**「我的策略跑 10 年最大回撤只有 20%」這句話，在沒有指定 $T$ 與 $\mu/\sigma$ 時毫無資訊量。**
同一個策略跑 20 年，若 $\mu=0$，期望 MDD 直接乘 $\sqrt{2}$。

### 7.3 Grossman–Zhou / Cvitanić–Karatzas 的動態回饋控制

限制：$W_t \ge \alpha M_t$（永遠不跌破歷史高點的 $\alpha$ 倍，即最大回撤 $\le 1-\alpha$）。
在 CRRA 效用下，最適風險資產比例是

$$\boxed{\;\pi_t = \pi_M \cdot \frac{1 - \dfrac{\alpha}{1-d_t}}{1-\alpha}\;}, \qquad
\pi_M = \frac{\mu - r}{\gamma\sigma^2} \ \text{(Merton 比例)}$$

檢查端點：
- $d_t = 0$（在高點）$\Rightarrow \pi = \pi_M$：滿倉，跟無約束一樣。
- $d_t = 1-\alpha$（觸及地板）$\Rightarrow \pi = 0$：完全出清。
- 中間單調遞減。

引入**正規化緩衝（cushion）** $\kappa_t = \dfrac{W_t - \alpha M_t}{W_t} = 1 - \dfrac{\alpha}{1-d_t}$，
則 $\pi_t = \pi_M \kappa_t/(1-\alpha)$——**槓桿對 cushion 是線性的**。

> **術語更正（筆記寫「convex defuse control law」）**：
> 這條控制律對 **cushion 是線性**，對 **回撤深度 $d$ 是凹的（concave）**：
> $\dfrac{\partial^2 \pi}{\partial d^2} = -\dfrac{2\alpha}{(1-\alpha)(1-d)^3} < 0$。
> 也就是回撤越深，**減碼速度越快**（加速去槓桿）——這是好的性質，
> 但它不叫 convex。把它說成 convex in drawdown 是錯的。
> 若要說 convex，正確的講法是：**槓桿是 cushion 的凸函數族中最保守的線性成員**，
> 或直接說「對回撤深度凹、加速去槓桿」。

### 7.4 給定 MDD 上限求最大槓桿（可直接用的公式）

這是筆記問的「給定 MDD 之下對於槓桿比率的最佳化」的閉式答案。

槓桿 $L$ 下，對數財富 $X_t = \nu t + s B_t$，其中
$$\nu = L(\mu - r) - \tfrac{1}{2}L^2\sigma^2, \qquad s = L\sigma$$

對 $\nu > 0$ 的漂移布朗運動，**全時間**最大回撤（對數尺度）$D_\infty$ 滿足

$$\mathbb{P}(D_\infty > x) = \exp\!\left(-\frac{2\nu x}{s^2}\right)$$

要求「回撤超過 $\mathrm{DD}$ 的機率 $\le \epsilon$」，令 $x = -\log(1-\mathrm{DD})$：

$$\exp\!\left(-\frac{2\nu x}{L^2\sigma^2}\right) \le \epsilon
\quad\Longleftrightarrow\quad
\frac{2\big[L(\mu-r) - \tfrac12 L^2\sigma^2\big]\,\big(-\log(1-\mathrm{DD})\big)}{L^2\sigma^2} \ge -\log\epsilon$$

整理後對 $L$ 數值求解（模組用 brentq）。極限情形驗算：
$\mathrm{DD}\to 1$ 時約束消失，$L \to$ full Kelly $(\mu-r)/\sigma^2$。符合直覺。

> **但書（這條最重要）**：上式假設 GBM。真實市場有跳空、厚尾與流動性斷層，
> 三者都讓實際回撤超過 GBM 的預測。此外這是**全時間**機率（比有限期更保守），
> 但保守的方向抵不過厚尾造成的低估。**實務上把算出來的 $L$ 再打對折**，
> 而且必須額外檢查 §7.5 的三個約束。模組的 `note` 欄位會把這段話帶出來。

### 7.5 筆記提到但公式抓不到的三件事

筆記寫「條件限制要考慮 margin requirement / trigger threshold / gap risk / fat-tail event」。
這四項全部是上面 GBM 模型抓不到的，必須另外處理：

1. **保證金追繳**是**路徑相依的離散事件**：不是「回撤 30%」而是
   「盤中某一刻權益率跌破維持率」。連續時間模型平滑掉了盤中極值。
   正確處理要用 $\sup_{t}$ 的 intraday 版本，或直接用 tick 資料模擬。
2. **Gap risk**：台指期夜盤/開盤跳空讓停損無法在停損價成交。
   任何用「停損 = 固定虧損」假設的 MDD 計算都低估了尾部。
3. **強制去槓桿的正回饋**：被追繳 → 被迫賣 → 價格更低 → 更多人被追繳。
   這讓「我的部位很小不影響價格」在最需要它成立的時候失效。
4. **CVaR 作為補充**：$\mathrm{CVaR}_\beta = \mathbb{E}[X \mid X \le \mathrm{VaR}_\beta]$
   是凸的、可用線性規劃最佳化（Rockafellar–Uryasev 2000），
   而 MDD 是路徑相依、非凸的。**用 CVaR 做最佳化、用 MDD 做驗收**，
   是實務上的分工。

**落地**：`strategies/_common/risk/drawdown.py`

---

## §8 「槓桿越大，策略要越簡單」

### 8.1 筆記原話

> 老闆說「槓桿越大 策略要越簡單」的原因：reduce execution risk / reduce overfitting /
> de-leveraging constraint。Quant 界常說："If you are going to smoke, you'd better have a very simple filter"

這句話可以**證明**，而且結論比直覺更強。

### 8.2 推導

對數成長率 $g(L) = L\mu - \tfrac12 L^2\sigma^2$，最大值在 $L^* = \mu/\sigma^2$。

設你用的槓桿有**相對誤差** $\delta$，即 $\hat L = L(1+\delta)$。成長損失：

$$g(L) - g\big(L(1+\delta)\big) = \tfrac{1}{2}\sigma^2 L^2 \delta^2$$

$$\boxed{\;\text{成長損失} \;\propto\; L^2 \delta^2\;}$$

**同樣的相對模型誤差，在兩倍槓桿下要付四倍代價。**

再接上第二步：一個用 $n$ 筆觀測擬合 $p$ 個自由參數的策略，
其參數估計的相對誤差平方尺度為 $\delta^2 \sim k\,p/n$
（這是 AIC / 有效自由度懲罰的同一個量級論證）。代入：

$$\text{成長損失} \approx \tfrac{1}{2}\sigma^2 L^2 \cdot \frac{k p}{n} \;\le\; \tau
\quad\Longrightarrow\quad
\boxed{\;p_{\max} = \frac{2\tau n}{k\,\sigma^2 L^2}\;}$$

### 8.3 結論

**可容許的模型複雜度隨槓桿以 $1/L^2$ 衰減。**

- 槓桿加倍 → 可用參數數量剩 1/4。
- 想維持複雜度而加槓桿 → 資料需求 $n$ 要以 $L^2$ 成長。

這就是老闆那句話的量化版本，也是 "if you are going to smoke,
you'd better have a very simple filter" 的數學內容：
高槓桿（抽菸）放大了每一個估計誤差的代價，所以濾網（模型）必須簡單到
它的估計誤差本身夠小。

> **但書**：$\delta^2 \sim kp/n$ 是**量級論證不是定理**。$k$ 是需要校準的經驗常數，
> 且對高度相關的參數、正則化模型、或非參數模型（樹、NN）都需要換成有效自由度。
> 模組 `complexity_budget()` 的 docstring 明寫這點，不假裝它是嚴謹結果。
> **但 $1/L^2$ 這個尺度關係本身是穩健的**——它只來自 $g$ 在極值附近的二階展開，
> 不依賴 $\delta^2 \sim kp/n$ 這個具體形式。

### 8.4 另外兩個理由（筆記有列，補上機制）

- **Execution risk**：高槓桿下，同樣的滑價 bps 吃掉的權益比例乘以 $L$。
  複雜策略通常換手率更高 → 滑價暴露更大 → 與 $L$ 相乘。
- **De-leveraging constraint**：見 §7.3。複雜策略的訊號在壓力時期
  常同時失效（相關性 → 1），此時 §7.3 的控制律要求快速減碼，
  但複雜策略的部位通常較難快速平倉。

---

## §9 處置股事件交易

### 9.1 筆記原話

> 重要日期：注意日、公告日、入獄日、出獄日。
> 常見策略：1. 入獄短期空 2. 主力鎖籌碼 all in 3. 出獄套利
> 常用指標：liquidity shock / crowding index / turnover rate / divergence
> 要考慮法規限制：shorting constraints / capital allocation

### 9.2 事件時間代數

對股票 $i$，定義事件時刻：

| 符號 | 意義 | 資料來源欄位 |
|---|---|---|
| $\tau^{\text{att}}_i$ | 注意日：首度被列注意股 | `is_attention_bool` 由 0→1 |
| $\tau^{\text{ann}}_i$ | 公告日：處置公告 | `is_disposition_bool` 首次為真的前一日 |
| $\tau^{\text{in}}_i$ | 入獄日：處置生效首日 | `is_disposition_bool` 0→1 |
| $\tau^{\text{out}}_i$ | 出獄日：處置結束後首個正常交易日 | `is_disposition_bool` 1→0 |

事件時間 $u = t - \tau^{\text{in}}_i$，所有分析在 $(i, u)$ 座標上做，
再跨 $i$ 平均得到事件研究的累積異常報酬 $\mathrm{CAR}(u)$。

**嚴重度分層**：`match_interval_sec` 直接給出撮合間隔——
約 300 秒 = 第一次處置（10 個營業日，5 分鐘撮合），
約 1200 秒 = 第二次以上（20 個營業日，20 分鐘撮合 + 預收款券）。
這比用 `disposition_count_30d` 推斷乾淨，因為它是規則的直接觀測值。

### 9.3 指標的可計算定義

**Liquidity shock**（相對於自身常態的成交萎縮）：
$$\mathrm{LS}_{i,t} = \log \frac{A_{i,t}}{\operatorname{median}\big(A_{i,t-21:t-1}\big)}$$
入獄後預期 $\mathrm{LS} \ll 0$：分盤撮合大幅降低成交。

**Crowding index**（筆記寫 "croding index"，應為 crowding）。
這個詞在文獻上沒有唯一定義，我用可得資料給兩個版本並在模組中都算：
$$\mathrm{CI}^{\text{holder}}_{i,t} = \texttt{pct\_over\_1000}_{i,t}
\quad\text{(大戶持股比，來自 } \texttt{tw\_chip\_dist\_daily}\text{)}$$
$$\mathrm{CI}^{\text{margin}}_{i,t} = \texttt{margin\_util\_pct}_{i,t}
\quad\text{(融資使用率 → 槓桿買盤的擁擠程度)}$$
前者對應筆記的「主力鎖籌碼」，後者對應「散戶槓桿多殺多」的燃料。

**Turnover rate**：$\mathrm{TO}_{i,t} = V_{i,t} / \text{流通股數}_i$。

### 9.4 三個策略的可檢定假設

$$H_1^{\text{in}}:\ \mathbb{E}\big[r_{i,u} \mid u \in [0, 2]\big] < 0 \quad \text{（入獄短空）}$$
$$H_1^{\text{lock}}:\ \mathbb{E}\big[r_{i,u} \mid u>0,\ \Delta \mathrm{CI}^{\text{holder}} > 0\big] > 0 \quad \text{（籌碼鎖定）}$$
$$H_1^{\text{out}}:\ \mathbb{E}\big[r_{i,u} \mid u \in [U-1, U+2]\big] > 0 \quad \text{（出獄套利，}U\text{ 為處置長度）}$$

### 9.5 法規約束：為什麼「入獄短空」多半做不到

筆記正確地把 "shorting constraints" 列為約束。用資料把它變成硬檢查：

1. **禁現沖**：`is_no_daytrade_bool` 為真時，當沖被禁。這砍掉了短線放空的主要工具。
   `tw_stock_trading_attrs_daily` 更細，分 `no_daytrade_buy_first`（禁先買後賣）
   與 `no_daytrade_sell_first`（禁先賣後買）——**後者才是禁放空**，兩者不同。
2. **停券**：處置期間券商常暫停融券。
   實證特徵是 `short_balance_lot` 在 $\tau^{\text{in}}$ 後掉到 0 或凍結。
3. **預收款券**：第二次處置要求預收，等於資金成本大幅上升。
4. **分盤撮合本身**：5 或 20 分鐘一次撮合 → 你的市價單無法在預期價格成交，
   滑價分布完全不同於連續交易。

> **這是本節最重要的判斷**：
> 一個沒有先驗證「這些股票在事件期間**實際上可以被放空**」的空方回測，
> 其績效是**不可實現的**。所以策略實作的第一步不是算訊號，
> 是算**可放空樣本的比例**。如果這個比例很低，正確的結論是
> 「這個策略不能做」，而不是把回測跑完然後報告 Sharpe。
> 我會先跑這個檢查再決定要不要實作空方腿。

### 9.6 資金配置

筆記提到 capital allocation。處置股的特殊之處：
成交量在事件期間萎縮一到兩個數量級，所以**部位上限應綁在事件期間的成交量**，
而不是事件前的成交量。用 $\min_{u \in [0,U]} A_{i,u}$ 的某個比例作為上限，
且這個量在 $\tau^{\text{in}}$ 之前**未知**——所以要用同類事件的歷史分位數做 ex-ante 估計。
這是一個真正的 PIT 陷阱：用事後實現的成交量算容量，會嚴重高估策略容量。

**落地**：`strategies/disposition_event_tw/`（見 §10）

---

## §10 落地對照表

| 節 | 模組 | 狀態 |
|---|---|---|
| §1, §2 | `strategies/_common/factors/volume.py` | 本次新增 |
| §3, §4 | `strategies/_common/factors/multiscale.py` | 本次新增 |
| §5 | `strategies/_common/validation/tradability.py` | 本次新增 |
| §6 | `strategies/_common/validation/reality_check.py` | 本次新增 |
| §7, §8 | `strategies/_common/risk/drawdown.py` | 本次新增 |
| §9 | `strategies/_common/qd.py`（資料層） | 本次新增 |
| §3.6 | `strategies/_common/validation/cpcv.py` | 既有 |
| §6.4 | `validation/sharpe.py`, `validation/pbo.py` | 既有 |

### 共通的驗證要求

每個時序函數都必須通過**無前視性 property test**：

```python
full = f(x)
for cut in (150, 200, 250):
    assert np.allclose(f(x[:cut])[-1], full[cut-1], equal_nan=True)
```

意思是：只給前 `cut` 筆資料算出來的最後一個值，
必須等於給全部資料算出來的第 `cut` 個值。
不成立即代表函數偷看了未來。這條測試比任何回測都更能抓出致命錯誤。

---

## §11 我對這份筆記的存疑與補充

誠實列出，避免把不確定的東西寫得像定論：

1. **`Tsang, Chang 2009 OBV` 查證不到。** 見 §1.3。不要引用未經查證的出處。
2. **「風暴比」應為「風報比」**（risk-reward ratio）的筆誤，
   且從上下文（Calmar / Sterling / Sortino）看，指的是**回撤型風報比**。
   模組按此實作三者。順帶一提：Sterling ratio 在文獻上**有兩種互不相容的定義**
   （原始定義分母是「年度最大回撤平均 + 10%」，現代常見版本是「N 個最大回撤的平均」），
   Sortino 的下方標準差**分母除以 N 還是除以下方樣本數**也有兩派。
   模組兩種都實作、都標明，因為不標明的話這些比率跨來源不可比。
3. **「以上三者比起 Sharpe 還有用」需要限定條件。**
   Calmar/Sterling/Sortino 對**非常態、路徑相依**的風險更敏感，這是對的；
   但它們的**估計誤差遠大於 Sharpe**（MDD 是單一極值統計量，
   一個樣本點決定整個分母）。所以：
   **報告時用它們，最佳化時用 Sharpe 或 CVaR。** 直接對 Calmar 做參數最佳化
   是過擬合的高速公路。
4. **筆記的 "convex defuse control law" 術語有誤**，見 §7.3。
5. **CNN/GNN 那條路與 §8 的 $1/L^2$ 定律直接衝突。**
   一個 $10^5$ 參數的模型要在高槓桿下使用，需要的資料量是天文數字。
   合理的用法是：**用 NN 產生低維特徵，用簡單規則決定部位**，
   而不是讓 NN 直接輸出部位大小。
6. **本 repo 的期貨連續序列只回溯到 2016-01-04**，股票日 K 回溯到 2010-01-04。
   任何跨兩者的研究窗口起點是 2016，這會讓樣本只剩約 2,595 個交易日——
   對照 §4.4 的樣本代價分析，這限制了能做幾層濾網。
