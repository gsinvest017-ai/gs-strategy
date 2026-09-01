# Continuous Timing Signals for Growth-Defensive Style Allocation: Factor Attribution, Risk Matching, and Out-of-Sample Evidence

Auto-generated bundle from `arxiv:2605.20636`.

Template: **momentum**

Matched keywords: `momentum`

Paper URL: http://arxiv.org/abs/2605.20636v2

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **momentum** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2605.20636",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2605.20636")`.

### Auto-retrieved passages

- **p.2** (BM25 -10.548):
  > vailable on GitHub at: https://github.com/ZheliXiong/ continuous-smooth-signals-growth-tech-defensive-income-allocation 2 Related Literature The first literature branch is empirical asset pricing. Fama and French (1993) and Fama and French (2015) provide the factor-attribution framework used to distinguish systematic style exposure from residual alpha. Carhart (1997) motivates the inclusion of momen- tum. In this paper, FF5 plus momentum attribution is not a side exercise; it defines the boundary of the interpretation. IfG−Dhas strong negative HML and positive momentum exposure, then the later timing exercise is more appropriately called factor or style timing. The second branch is return pr …

- **p.1** (BM25 -10.43):
  > Continuous Timing Signals for Growth–Defensive Style Allocation Factor Attribution, Risk Matching, and Out-of-Sample Evidence Zheli Xiong Corresponding author: Zheli Xiong (zlxiong@mail.ustc.edu.cn) Abstract This paper studies conditional allocation between a growth/technology ETF basket, denoted byG, and a defensive income/value-oriented ETF basket, denoted byD. The objective is not to discover a new standalone alpha factor, but to examine whether known style exposures can be dynamically allocated using macro- market timing signals. Fama–French five-factor plus momentum attribution shows that the relative portfolioG−Dis a recognizable style portfolio: its market beta is 0.273, its HML beta  …

- **p.2** (BM25 -10.43):
  > growth/technology basketGis a fixed equal-weight portfolio of QQQ, XLK, VGT, SPYG, and VUG. The defensive income basketDis a fixed equal-weight portfolio of SCHD, VYM, VTV, FDVV, and COWZ. The central relative return is RG−D t =R G t −R D t .(1) The research question is deliberately narrower than a search for a new alpha. Before studying conditional allocation, the paper first asks whatG−Dis in factor terms. If G−Dis mostly high market beta, negative value exposure, positive momentum exposure, and aggressive investment exposure, then the relevant empirical question is not whether the portfolio is a new anomaly. It is whether these known style exposures can be managed more effectively through …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
