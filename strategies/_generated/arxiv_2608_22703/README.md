# Diagonal Frog meets ADI: trading matrix exponentials for rational maps in the Fokker--Planck equation

Auto-generated bundle from `arxiv:2608.22703`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2608.22703v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.22703",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.22703")`.

### Auto-retrieved passages

- **p.14** (BM25 -2.892):
  > ive, and the obstruction is structural rather than a matter of how the mixed derivative is treated. A stage of a stabilizing-correction scheme has the form Yj = ( I−θ∆tFj )−1[ Yj−1−θ∆tFj pn ] ,(21) and the operand in brackets carries a subtraction. Under the conservative closure1⊤Fj = 0, soFjpn sums to zero and, unlesspn is stationary forFj, has entries of both signs. The operand is therefore signed for every nonnegative pn of interest, and entrywise nonnegativity of the matrix in front of it constrains its action on the nonnegative cone only. The positivity of the resolvent, or of any other factor placed in that position, is simply not used. Replacing the resolvent by the Padé(0, 2)map of S …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
