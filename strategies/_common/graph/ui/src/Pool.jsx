import React, { useEffect, useState } from "react";
import { api, fmt } from "./model";

const ORIGIN = {
  "gs-strategy": "gs-strategy",
  "gs-strategy-graph": "gs-strategy（組合圖）",
  external: "外部匯入",
  "manual-md": "手動匯入（MD）",
  "manual-py": "手動匯入（PY）",
  builtin: "gs-zipline-tej 範例",
};

export function StrategyMenu({ current, disabled, onSelect }) {
  const [pool, setPool] = useState(null), [error, setError] = useState("");
  const load = (refresh = false) =>
    api("/strategies" + (refresh ? "?refresh=1" : ""))
      .then((p) => { setPool(p); setError(p.pool_error || ""); })
      .catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);
  const groups = {};
  for (const s of pool?.strategies || []) (groups[s.origin] ||= []).push(s);
  const fixture = pool?.fixture;
  return (
    <span className="strategy-menu">
      <select data-testid="strategy-menu" value={current || ""} disabled={disabled || !pool || fixture}
              title={fixture ? "測試資料模式只能檢視目前的圖" : "切換策略池中的策略"}
              onChange={(e) => onSelect(e.target.value)}>
        {!current && <option value="">選擇策略…</option>}
        {current && !(pool?.strategies || []).some((s) => s.id === current) && <option value={current}>{current}</option>}
        {Object.entries(groups).map(([origin, list]) => (
          <optgroup key={origin} label={ORIGIN[origin] || origin}>
            {list.map((s) => (
              <option key={s.id} value={s.id} disabled={!s.selectable}>
                {s.name && s.name !== s.id ? `${s.id} — ${s.name}` : s.id}
                {s.graph === "composed" ? "（完整圖）" : "（粗圖）"}
              </option>
            ))}
          </optgroup>
        ))}
        {(pool?.factors || []).length > 0 && (
          <optgroup label={`因子池（${pool.factors.length}，第二期接入）`}>
            {pool.factors.map((f) => <option key={f.id} value={f.id} disabled>{f.id}</option>)}
          </optgroup>
        )}
      </select>
      <button className="icon" disabled={disabled} onClick={() => load(true)} title="重新掃描策略池" aria-label="重新掃描策略池">⟳</button>
      {error && <span className="pool-error" title={error}>策略池：{error}</span>}
    </span>
  );
}

function Equity({ points }) {
  if (!points?.length) return <p className="muted">沒有報酬序列（執行未產生績效）</p>;
  const W = 640, H = 120;
  const ys = points.map((p) => p[1]);
  const lo = Math.min(...ys), hi = Math.max(...ys), span = hi - lo || 1;
  const d = points.map((p, i) => `${i ? "L" : "M"}${(i / Math.max(1, points.length - 1)) * W},${H - ((p[1] - lo) / span) * (H - 8) - 4}`).join("");
  return (
    <svg className="results-equity" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label="權益曲線">
      <path d={d} />
      <text x="4" y="12">{fmt(hi)}</text>
      <text x="4" y={H - 4}>{fmt(lo)}</text>
      <text x={W - 4} y={H - 4} textAnchor="end">{points[0][0]} → {points[points.length - 1][0]}</text>
    </svg>
  );
}

export function Results({ strategy, close, revision }) {
  const [rows, setRows] = useState(null), [all, setAll] = useState(false);
  const [detail, setDetail] = useState(null), [error, setError] = useState("");
  useEffect(() => {
    api("/results?limit=200" + (all || !strategy ? "" : "&strategy=" + encodeURIComponent(strategy)))
      .then((r) => setRows(r.runs)).catch((e) => setError(e.message));
  }, [strategy, all, revision]);
  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") close(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [close]);
  const open = (id) => api("/results/" + id).then(setDetail).catch((e) => setError(e.message));
  return (
    <div className="replay-overlay results-overlay" role="dialog" aria-label="回測結果紀錄">
      <header>
        <button className="replay-back" onClick={close}>← 返回策略圖</button>
        <div className="replay-title">
          <small>BACKTEST RESULTS</small>
          <h2>回測結果紀錄（data/backtests.sqlite）</h2>
        </div>
        <label className="results-all">
          <input type="checkbox" checked={all} onChange={(e) => setAll(e.target.checked)} /> 所有策略
        </label>
      </header>
      {error && <p className="error-banner">{error}</p>}
      <div className="replay-bottom">
        {rows && !rows.length && <p className="muted">尚無紀錄。每次按「執行」都會自動寫入一筆，包含被拒絕的執行。</p>}
        {rows && rows.length > 0 && (
          <table className="replay-table results-table">
            <thead>
              <tr><th>時間（UTC）</th><th>策略</th><th>狀態</th><th>試驗</th><th>N</th><th>模型／引擎</th>
                <th>Sharpe</th><th>DSR</th><th>MDD</th><th>CAGR</th><th>天數</th></tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.run_id} className={detail?.run_id === r.run_id ? "active" : ""} onClick={() => open(r.run_id)}>
                  <td className="mono">{r.recorded_at.slice(0, 19).replace("T", " ")}</td>
                  <td>{r.strategy}</td>
                  <td className={r.status === "complete" ? "ok" : "bad"} title={r.message || ""}>{r.status === "complete" ? "完成" : "失敗／拒絕"}</td>
                  <td>{r.new_trial ? "新試驗 +1" : r.backtest_key ? "快取重播" : "—"}</td>
                  <td>{r.selection_n ?? "—"}</td>
                  <td>{r.model || (r.engine || "").replace("backtest.", "")}</td>
                  <td>{fmt(r.sharpe)}</td><td>{fmt(r.dsr)}</td><td>{fmt(r.max_drawdown)}</td><td>{fmt(r.cagr)}</td>
                  <td>{r.n_days ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {detail && (
          <section className="results-detail">
            <h3>{detail.strategy}・{detail.recorded_at.slice(0, 19).replace("T", " ")}</h3>
            {detail.message && <p className="bad">{detail.message}</p>}
            <Equity points={detail.equity} />
            <p className="mono muted">backtest_key {detail.backtest_key || "—"}・graph {String(detail.graph_hash || "—").slice(0, 12)}</p>
            {detail.details?.walk_forward && (
              <p>walk-forward：OOS {detail.details.walk_forward.oos_start} → {detail.details.walk_forward.oos_end}，
                {detail.details.walk_forward.folds?.length} 個 fold，買進持有 Sharpe {fmt(detail.details.walk_forward.benchmark_sharpe)}</p>
            )}
            {detail.details?.report?.warnings?.map((w, i) => <p key={i} className="warning-text">⚠ {w}</p>)}
            <details>
              <summary>參數快照</summary>
              <pre className="cot">{JSON.stringify(detail.params, null, 2)}</pre>
            </details>
          </section>
        )}
      </div>
    </div>
  );
}
