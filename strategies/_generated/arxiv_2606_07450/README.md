# Information Networks of Stock Prices

Auto-generated bundle from `arxiv:2606.07450`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.07450v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.07450",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.07450")`.

### Auto-retrieved passages

- **p.2** (BM25 -3.487):
  > s and business groups to broader market hierarchies that depict the spectral collectivity of price movements on the trading floor [22], [23]. The most commonly used approach in relational calculations between stock price movements is the Pearson correlation. This approach is statistically stable in detecting linear co-movements. However, by definition, Pearson correlation is not designed to capture non-linear dependencies,tail dependence, or non-Gaussianrelationships that frequently arise in financial return dynamics [5]. Efforts to sharpen the correlative patterns provided by the Pearson correlation approach include, among others, the transfer entropy approach, which produces directed netwo …

- **p.6** (BM25 -3.141):
  > Substituting this local density approximation into the definition of differential entropy and replacing the expectation with a sample average yields the Kozachenko–Leonenko estimator [14]: hKL(X) =ψ(N)−ψ(k) + logc d + d N X i logϵ i (24) A problem arises when h(X), h(Y), and h(X,Y) are all estimated separately and then substituted into I(X;Y) =h(X) +h(Y)−h(X, Y). In finite samples, the biases of these three estimators do not cancel each other well. Kraskov–Stögbauer–Grassberger (KSG) [3] addresses this issue by first finding the radius ϵi to the k-th nearest neighbor in the joint space (X,Y), usually under thesup normorChebyshev metric, then counting the number of neighbors falling within th …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
