# A Spectral Generalisation of the Variance Ratio: Eigenstructure of Long-Horizon Portfolio Covariance and a Multi-Memory Factor Model of U.S. Equity Returns

Auto-generated bundle from `arxiv:2607.03858`.

Template: **momentum**

Matched keywords: `momentum`

Paper URL: http://arxiv.org/abs/2607.03858v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **momentum** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.03858",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.03858")`.

### Auto-retrieved passages

- **p.1** (BM25 -9.938):
  > arrower dating. (iii) The cross-sectional loadings driving return- channel long memory are economically distinct from those driving volatility-channel cascade memory: a cross-channelβ-inversion test finds no panel exhibits the positive cross-channel alignment that a single shared loading predicts, and rejects the shared-loading hypothesis toward anti-alignment on the two largest panels at Bonferronip= 0.0004. Industry and size×book-to-market characteristics that predict return-momentum patterns therefore need not predict volatility-persistence patterns. JEL Classification:G11, G12, C58, C32. Keywords:variance ratio test, principal component analysis, long-horizon portfolio dynamics, multifra …

- **p.51** (BM25 -9.443):
  > ert A. Korajczyk. A test for the number of factors in an approximate factor model.The Journal of Finance, 48(4):1263–1291, 1993. URLhttps://www.jstor. org/stable/2329038. Rama Cont. Empirical properties of asset returns: Stylized facts and statistical issues.Quanti- tative Finance, 1(2):223–236, 2001. doi: 10.1080/713665670. Zhuanxin Ding, Clive W. J. Granger, and Robert F. Engle. A long memory property of stock market returns and a new model.Journal of Empirical Finance, 1(1):83–106, 1993. doi: 10.1016/0927-5398(93)90006-D. Sina Ehsani and Juhani T. Linnainmaa. Factor momentum and the momentum factor.Journal of Finance, 77(3):1877–1919, 2022. doi: 10.1111/jofi.13131. Eugene F. Fama and Kenn …

- **p.39** (BM25 -7.216):
  > tion predictsκAR(p) as a signed convex combination of AR(1) vari- ance ratios indexed by the characteristic roots. The vector AR(1) specification with eigenvector- mixing perturbation predicts anOwith Lorentzian eigenvalue-gap dependence and saturating horizon amplification factorS1/c→1/(1−¯ρ2). Empirically on the Fama–French 49-industry universe over 1969–2026, the framework recovers the Jegadeesh–Titman and De Bondt–Thaler patterns at the market mode, identifies persistent factor momentum in the sub-leading modes, demonstrates eigenvalue-gap-dependent eigenvector stability with a stable market mode and a curiously stable deepest eigenmode, and inverts to AR(2) characteristic roots that inc …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
