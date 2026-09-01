# From Index to Equity: Pre-Training Transformers for Stock Return Prediction

Auto-generated bundle from `arxiv:2605.23962`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2605.23962v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2605.23962",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2605.23962")`.

### Auto-retrieved passages

- **p.5** (BM25 -4.336):
  > was used for regression. The XGBoost model was trained with the parameters defined in table 1. Table 1: Parameters used for training the XGBoost model Parameter Value Number of Estimators 100 Learning Rate 0.03 Maximum Depth 9 Column Sample by Tree 0.7 Maximum Leaves 100 3. Experiment The first experiment compared two transformer -based approaches for individual stock prediction: one trained with randomly initialized weights and another initialized using weights from a model pre-trained on the market index. For the pre -training stage, historical index data underwent the same preprocessing and feature engineering procedures as the individual stock data. Both models were trained to classify t …

- **p.5** (BM25 -4.32):
  > The transformer architecture consisted of four transformer encoder blocks followed by three fully connected dense layers with 128, 64, and 32 nodes, respectively. All dense layers used the ReLU activation function, and positional encoding was applied to the input sequences. For the LSTM benchmark models, the transformer encoder blocks were replaced with four LSTM layers. An overview of the model architecture is presented in Figure 2. Figure 2. Layers in transformer encoder architecture For the classification task, the output layer consisted of a dense layer with a single node and a sigmoid activation function. For the regression task, the output layer also consisted of a single-node dense la …

- **p.10** (BM25 -2.667):
  > recommendations. A risk -control strategy proposed in [6] involved excluding stocks with high historical prediction error over the most recent 40 -day period from portfolio selection, and this approach could be incorporated into the application layer. Finally, to leverage recent advances in large language models (LLMs), future research could explore transformer architectures that incorporate pre-trained components derived from LLMs. References 1. Z. Liu, "Chaotic Time Series Analysis," Mathematical Problems in Engineering, vol. doi:10.1155/2010/720190, 2010. 2. D. Kisiel and D. Gorse, "Portfolio Transformer for Attention-Based Asset Allocation," arXiv:2206.03246v1, 2022. 3. A. Vaswani, N. Sh …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
