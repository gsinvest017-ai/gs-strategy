# Diagonal Frog: High-order positivity-preserving FD schemes for anisotropic Fokker-Planck equations

Auto-generated bundle from `arxiv:2606.23980`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.23980v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.23980",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.23980")`.

### Auto-retrieved passages

- **p.51** (BM25 -5.848):
  > ), ν=t i−ti−1.(A.2) Thus, to define non-negativity preserving FD scheme we need to extend the above definitions to the discrete case. Definition A.3.A real-valued vectorx= [x 1,...,xN]is nonnegative, ifx i≥0∀i∈[1,N]. Definition A.4.Given a formal solution of the linear PDE in the form of Eq. (A.2), this solution is called non-negativity preserving, ifp(ti−1,x)is a nonnegative vector, andp(ti,x)is also a nonnegative vector. Definition A.5.An arbitrary matrixA={aij}, i∈[1,N], j∈[1,M]is called nonnegative if aij≥0,∀i,j. From Definitions A.4 and A.5 it immediately follows that Proposition 15.The solution Eq.(A.2)is non-negativity preserving, ife νLis a nonnegative matrix. Proof.The proof directl …

- **p.9** (BM25 -5.097):
  > I−Ais never eventually nonnegative and no representation of the form Definition A.12 exists; moreovere−sApossesses negative entries for all soutside a discrete set. Page 9 of 64

- **p.51** (BM25 -5.013):
  > that will play a central role in constructing the FD algorithms described throughout this paper. Definition A.6.A matrix is called aZ-matrixif all its off-diagonal entries are non-positive. Equivalently, a Z-matrixZ= (z ij)satisfies zij≤0, i̸=j. Definition A.7.LetA= (a ij)be anN×Nreal Z-matrix, so that aij≤0∀i̸=j,1≤i,j≤N. ThenAis called anM-matrixif it admits the representationA=sI−B, where B= (b ij), b ij≥0∀1≤i,j≤N, Iis the identity matrix, andsexceeds the spectral radius ofB. An immediate consequence of the Perron–Frobenius theorem [Bellman, 1970] is that any non-singular M-matrixAsatisfies: Page 51 of 64

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
