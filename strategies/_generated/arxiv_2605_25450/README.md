# Valuation of Variable Annuities with Equity Protection Swaps under Jumps and Default Risks

Auto-generated bundle from `arxiv:2605.25450`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2605.25450v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2605.25450",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2605.25450")`.

### Auto-retrieved passages

- **p.13** (BM25 -6.563):
  > EQUITYPROTECTIONSWAPS13 Definition 4.1.For a standard EPS introduced by Xu et al. [19], the provider’shedged cash flowfor one unit of the nominal principalN p, assessed at maturityTand denoted byCF T(c,H), equals CFT(c,H) = (c−H(0))e rT +H(T) +ψ(R T)(15) whereψ(R T)is given in Lemma 2.1. The hedging strategy presented in Proposition 4.1 isa static hedging strategythat we can find a premium bc∈Rsuch the equalityCF T(bc,H) =0 holds almost surely. Andbcis called thefair premiumfor a standard EPS per one unit of the nominal principal. With the static hedging strategy for the standard EPS products, we now want to find the hedging strategies under consideration of jumps and default risks. We will  …

- **p.19** (BM25 -6.236):
  > EQUITYPROTECTIONSWAPS19 DA=E(DA|P D)×P D =P D × ∞ ∑ n=0 Q(NT =n)×E(DA|N T =n), then we will have the default adjustment.2 Default-adjusted initial premium In conclusion, with the default adjustment for the independent random time default events, we have the following proposition for the default adjusted initial premium. Proposition 4.5.Under a general hedging strategy without consideration of default, the EPS provider uses a hedging portfolio built in Proposition 4.1 with an initial value at time0as follows, H(0) = n ∑ i=0 pi+1 −p i S0 Put0(Kl i,T)− m ∑ j=0 fj+1 −f j S0 Call0(Kg j ,T) where Kl i =S 0(1+l i)and K g j =S 0(1+g j)for every i=0, 1, . . . ,n and j=0, 1, . . . ,m. Assuming only th …

- **p.5** (BM25 -5.765):
  > roduce the jump model to the underlying asset valuation. Here we will give the definition of the general jump model - the jump- diffusion model, which we will use to discuss the influence of jumps on the pricing and hedging of standard EPS products in this paper. Besides jumps, cancellation risks and execution risks of the options should also included in the consideration of EPS products’ hedging strategy, especially after the consideration of jumps. It is important to note that credit risks will have a significant impact on the hedging strategies and fair initial premiums of the standard EPS with consideration of jumps. In this paper, we will discuss the independent random time default even …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
