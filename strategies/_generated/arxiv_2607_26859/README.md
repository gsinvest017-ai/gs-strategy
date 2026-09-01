# No Data Is Not No Risk: Visibility Aware Graph-Based Inference of Business Conduct Risk

Auto-generated bundle from `arxiv:2607.26859`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2607.26859v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.26859",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.26859")`.

### Auto-retrieved passages

- **p.6** (BM25 -3.609):
  > regate conclusions about relation importance are based on the ablation results rather than this single example. RQ5: Does graph-based inference retain predictive value among firms with no previously recorded incidents? Among the entities with no recorded incident before 2024, Lift@10%data is 2.37 (Table 4). The ranking therefore retains its predictive value among firms that entered the reference year without an incident history, although some of these firms may become labeled positives during 2024. Figure 4 applies a definition of visibility that is stricter than that used in Table 4 for the prediction cutoff: visible entities must have at least one incident recorded before 2025, whereas non …

- **p.3** (BM25 -3.435):
  > eteroge- neous extension of GCNII, which we callHeteroGCNII. Standard graph convolution aggregates normalized information from adja- cent nodes [ 13]. GCNII augments this operation with an initial residual connection and an identity mapping, which helps pre- serve node specific information and reduce over-smoothing across multiple graph convolution layers [3]. To model the directed, multi- relational ownership graph, HeteroGCNII applies an independent GCNII propagation channel to each directed relation type, following the general principle of relational graph convolution [18]. The input features are first projected into a shared hidden repre- sentation: 𝐻 (0) =𝜎 (𝑋𝑊in +𝑏 in) ,(5) where 𝑊in a …

- **p.4** (BM25 -2.966):
  > Tsuyoshi Iwata, Johannes Laurmaa, and Ryohei Hisano At graph convolution layer ℓ, each directed relation type 𝑟∈ R is processed by an independent GCNII propagation operator: 𝑀 (ℓ) 𝑟 =G (ℓ) 𝑟  𝐻 (ℓ) , 𝐻 (0) , 𝐸𝑟  .(6) The relation specific representations are aggregated by summa- tion: 𝐻 (ℓ+1) =𝜎 ∑︁ 𝑟∈ R 𝑀 (ℓ) 𝑟 ! .(7) Each relation channel has its own trainable parameters, while the initial representation 𝐻 (0) is shared across channels. Because for- ward and reverse company relationships are represented as separate elements of R, the model can learn asymmetric contributions for opposite directions of the same underlying relationship. After𝐿layers, the score for target entity𝑣is 𝑓𝜃 (𝑣)=𝑤 ⊤ …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
