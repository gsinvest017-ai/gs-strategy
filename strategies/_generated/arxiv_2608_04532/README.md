# Optimal Life Insurance Decision in Mean-Variance DC Management with Mortality Improvements

Auto-generated bundle from `arxiv:2608.04532`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2608.04532v2

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.04532",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.04532")`.

### Auto-retrieved passages

- **p.11** (BM25 -7.82):
  > ≤ E[(YT )2]. Consequently, (π ∗, I ∗) is the globally optimal strategy for the mean-variance opti mization problem. Proof. See Appendix G. 4 Numerical analysis 4.1 Model calibration This section provides a numerical illustration of the optimal strateg ies and the implied eﬃ- cient frontier. Baseline parameters for the ﬁnancial market and t he contribution dynamics are not separately estimated in this paper; they are adopted from standard values in the literature, primarily following Munk and Sørensen (2010). We consider a pension plan member who enters the plan at the age of x0 = 22 and retires at age 67. The accumulation period of this individual is therefore T = 45 years. The initial wealt …

- **p.16** (BM25 -7.771):
  > gher interest rate Sharpe ratio λ r raises the return on bonds and partially replaces the speculative demand for stocks. Therefore, π ∗ Bond rises and shifts from a short position to a long position at an earlier age (Figure 6(a)), while π ∗ Stock drops moderately (Figure 6(b)). The eﬀect on insurance needs is very limited, suggesting that λ r inﬂuences the investment strategy more signiﬁcantly. The proportion-to-wealt h plots in Figures 6(d)–6(f) also support this. A higher stock Sharpe ratio λ S raises the expected return of stocks per position. Since our retirement target is ﬁxed, a higher per-position return on sto cks means individuals can achieve the same total return with smaller posi …

- **p.15** (BM25 -5.615):
  > s they approach retir ement. However, as shown in Figures 4(d) and 4(e), this investment change is relatively small and doesn’t change the proportions allocated between bond and stock. In contrast, the mortality improvement signiﬁcantly changes the life insurance strategy both in amount and proportion (see Figures 4(c) and 4(f)). In particular, a longer life expectancy leads to a higher expected present value of future income. This pushes the protection needs toward early a dulthood, and because of this early shift, mid-to-late-life insurance allocation drops. 4.4 Sensitivity analysis In this section, we conduct a comprehensive sensitivity analysis to e xamine how key economic and model sett …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
