# AWARE-FX: An Auditable Knowledge-Guided AI System for Measuring Corporate Foreign-Exchange Hedging Disclosure

Auto-generated bundle from `arxiv:2607.27611`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2607.27611v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.27611",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.27611")`.

### Auto-retrieved passages

- **p.7** (BM25 -3.555):
  > n be difficult to detect and can vary across currencies, firms, windows, and stress states (Bartram et al., 2010). The disclosure score is not a hedge ratio, derivative notional, or causal treatment. A firm can hedge economically while disclosing little, and a firm can disclose extensively because its underlying risk is high. The exposure analysis therefore serves as external construct validation: a channel-specific disclosure measure should provide more discriminating information for linked FX-risk screening than a generic hedging-language score. The design does not infer that disclosure or hedging causes lower exposure. 2.6. Position relative to prior approaches The novelty of AWARE-FX lie …

- **p.34** (BM25 -3.457):
  > n of this manuscript, the author used OpenAI Codex and Google Gemini via Antigravity for language editing, LaTeX formatting, code review, and plotting assistance. Qwen3-8B and Gemini-based outputs were also used in the fixed-prompt benchmarks reported in the study. The author reviewed and edited all manuscript content, verified the reported cal- culations against archived outputs, and takes full responsibility for the work. References Adler, M., Dumas, B., 1984. Exposure to currency risk: Definition and measurement. Financial Management 13, 41–50. Allayannis, G., Ofek, E., 2001. Exchange rate exposure, hedging, and the use of foreign currency derivatives. Journal of International Money and F …

- **p.4** (BM25 -3.384):
  > i- fact is a reproducible measurement pipeline; the exposure analysis evaluates whether the artifact produces economically discriminating information. This positioning is consistent with design-science evaluation (Hevner et al., 2004; Gregor and Hevner, 2013), text-as-data measurement (Gentzkow et al., 2019; Grimmer and Stewart, 2013), financial textual analysis (Loughran and Mc- Donald, 2011; Hassan et al., 2019), and corporate risk-management research (Smith and Stulz, 1985; Allayannis and Ofek, 2001; Bartram et al., 2010). The remainder of the paper is organized as follows. Section 2 reviews related research and states the system’s position relative to recent financial LLM work. Section 3 …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
