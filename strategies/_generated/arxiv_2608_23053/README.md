# tse_tick: A Python Library for Parsing and Querying Nikkei NEEDS Tick Data from the Tokyo Stock Exchange

Auto-generated bundle from `arxiv:2608.23053`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2608.23053v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.23053",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.23053")`.

### Auto-retrieved passages

- **p.11** (BM25 -2.993):
  > l four data types, both schema eras, and both access paths, and an independent beta pass over a three-year ingestion—and are reported in Appendix A. 9 Security and Robustness The library treats untrusted archives and user-supplied query parameters defensively; Table 8 summarizes the guards, whose values are deliberate design decisions rather than defaults. Archives are validated before they are decompressed. Every entry is checked against a decompressed-size ceiling, a compression ratio, and an entry count before any bytes are ex- panded, and a violation raises SuspiciousZipError instead of filling memory or disk. A NEEDS archive holds a single CSV, so a five-entry ceiling is generous for le …

- **p.8** (BM25 -2.658):
  > le day to a multi-year range, resumes interrupted runs by default, and sizes its worker pool automatically; export writes CSV or Parquet chosen by the output extension, and --store switches it to the two-stage path. 7 Performance Evaluation To validate the design choices described above, we benchmarked the processing pipeline on repre- sentative files for all four NEEDS data types from January 2017. The headline comparison uses HTICST120 (individual stock ticks, 4.8 million rows, 95 columns). Two pandas [ 7] baselines are reported: the original prototype, which uses the Python CSV engine ( engine='python') because the NEEDS CSV has ragged lines that the C engine rejects without additional co …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
