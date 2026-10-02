import React, { useEffect, useMemo, useState } from "react";
import { api, fmt } from "./model";

const W = 960;
const H = { price: 150, equity: 120, position: 34, gap: 14 };
const pct = (v) => (v == null ? "—" : `${(v * 100).toFixed(2)}%`);
const dirText = { 1: "做多", "-1": "做空", 0: "空手" };

function scale(values, lo, hi) {
  const finite = values.filter((v) => v != null && Number.isFinite(v));
  if (!finite.length) return () => (lo + hi) / 2;
  let min = Math.min(...finite), max = Math.max(...finite);
  if (min === max) { min -= 1; max += 1; }
  return (v) => hi - ((v - min) / (max - min)) * (hi - lo);
}

function path(days, key, x, y) {
  let d = "", open = false;
  days.forEach((day, i) => {
    const v = day[key];
    if (v == null) { open = false; return; }
    d += `${open ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`;
    open = true;
  });
  return d;
}

export function ReplayChart({ data, cursor, onPick }) {
  const days = data.days;
  const n = Math.max(1, days.length - 1);
  const x = (i) => 40 + (i / n) * (W - 56);
  const top = 8, eqTop = top + H.price + H.gap, posTop = eqTop + H.equity + H.gap;
  const height = posTop + H.position + 18;
  const yPrice = scale(days.map((d) => d.settle), top, top + H.price);
  const yEq = scale(days.flatMap((d) => [d.equity, d.benchmark]), eqTop, eqTop + H.equity);
  const firstClean = days.findIndex((d) => !d.contaminated);
  const dirtyEnd = firstClean < 0 ? days.length - 1 : firstClean;
  const index = new Map(days.map((d, i) => [d.date, i]));
  const cursorIndex = index.get(cursor);
  const folds = data.folds.map((f) => index.get(f.test_start)).filter((i) => i != null);
  const pick = (event) => {
    const box = event.currentTarget.getBoundingClientRect();
    const rel = ((event.clientX - box.left) / box.width) * W;
    const i = Math.round(((rel - 40) / (W - 56)) * n);
    if (i >= 0 && i < days.length) onPick(days[i].date);
  };
  return (
    <svg className="replay-chart" viewBox={`0 0 ${W} ${height}`} onClick={pick} role="img"
         aria-label="價格、權益與部位回放圖">
      <defs>
        <pattern id="dirty" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <line x1="0" y1="0" x2="0" y2="6" className="dirty-hatch" />
        </pattern>
      </defs>
      {dirtyEnd > 0 && (
        <g>
          <rect x={x(0)} y={top} width={x(dirtyEnd) - x(0)} height={posTop + H.position - top}
                fill="url(#dirty)" className="dirty-zone" />
          <text x={x(0) + 6} y={top + 14} className="zone-label">知識截止前・已污染・不計績效</text>
        </g>
      )}
      {folds.map((i, k) => (
        <line key={k} x1={x(i)} x2={x(i)} y1={eqTop} y2={posTop + H.position} className="fold-line" />
      ))}
      <text x={4} y={top + 10} className="axis-label">價格</text>
      <path d={path(days, "settle", x, yPrice)} className="line price" />
      <text x={4} y={eqTop + 10} className="axis-label">權益</text>
      <path d={path(days, "benchmark", x, yEq)} className="line benchmark" />
      <path d={path(days, "equity", x, yEq)} className="line equity" />
      <text x={4} y={posTop + 12} className="axis-label">部位</text>
      {days.map((d, i) => d.position ? (
        <rect key={d.date} x={x(i)} width={Math.max(1, (W - 56) / n)} y={d.position > 0 ? posTop : posTop + H.position / 2}
              height={H.position / 2 * Math.min(1, Math.abs(d.position))}
              className={d.position > 0 ? "pos long" : "pos short"} />
      ) : null)}
      <line x1={40} x2={W - 16} y1={posTop + H.position / 2} y2={posTop + H.position / 2} className="zero" />
      {cursorIndex != null && (
        <line x1={x(cursorIndex)} x2={x(cursorIndex)} y1={top} y2={posTop + H.position} className="cursor" />
      )}
      <text x={40} y={height - 4} className="axis-label">{days[0]?.date}</text>
      <text x={W - 16} y={height - 4} textAnchor="end" className="axis-label">{days[days.length - 1]?.date}</text>
    </svg>
  );
}

function Features({ features }) {
  const rows = Object.entries(features || {});
  if (!rows.length) return null;
  return (
    <table className="replay-table">
      <tbody>
        {rows.map(([k, v]) => (
          <tr key={k}><th>{k}</th><td className="mono">{v == null ? "—" : fmt(v)}</td></tr>
        ))}
      </tbody>
    </table>
  );
}

export function Replay({ close, revision }) {
  const [data, setData] = useState(null), [error, setError] = useState("");
  const [at, setAt] = useState(0), [playing, setPlaying] = useState(false);
  useEffect(() => {
    let alive = true;
    api("/replay").then((d) => { if (alive) setData(d); }).catch((e) => alive && setError(e.message));
    return () => { alive = false; };
  }, [revision]);
  const decisions = data?.decisions || [];
  useEffect(() => {
    const first = decisions.findIndex((d) => d.called && !d.contaminated);
    setAt(first < 0 ? 0 : first);
  }, [data]);
  useEffect(() => {
    if (!playing) return undefined;
    const t = setInterval(() => setAt((i) => {
      if (i + 1 >= decisions.length) { setPlaying(false); return i; }
      return i + 1;
    }), 900);
    return () => clearInterval(t);
  }, [playing, decisions.length]);
  const card = decisions[at];
  const byDate = useMemo(() => new Map(decisions.map((d, i) => [d.date, i])), [decisions]);
  const pickDay = (date) => {
    let best = 0;
    decisions.forEach((d, i) => { if (d.date <= date) best = i; });
    setAt(byDate.get(date) ?? best);
  };
  return (
    <div className="replay-overlay" role="dialog" aria-label="walk-forward 回放">
      <header>
        <div>
          <small>WALK-FORWARD REPLAY</small>
          <h2>回放：資料 → 推論 → 決策 → 損益</h2>
        </div>
        <button onClick={close} aria-label="關閉回放">×</button>
      </header>
      {error && <p className="error-banner">{error}</p>}
      {data && !data.available && <p className="replay-empty">{data.reason}</p>}
      {data?.available && (
        <>
          <div className="replay-meta">
            <span>模型 <b>{data.model}</b></span>
            <span title={data.cutoff_basis}>知識截止上界 <b>{data.cutoff}</b></span>
            <span>乾淨樣本起點 <b>{data.clean_start}</b></span>
            <span>{data.anonymize ? "提示已匿名（無日期與標的名稱）" : "提示含日期與標的"}</span>
            {data.summary && (
              <>
                <span>OOS <b>{data.summary.oos_start} → {data.summary.oos_end}</b>（{data.summary.oos_days} 日）</span>
                <span>OOS Sharpe <b>{fmt(data.summary.oos_sharpe)}</b> vs 買進持有 <b>{fmt(data.summary.benchmark_sharpe)}</b></span>
                <span>{data.folds.length} 個 fold</span>
              </>
            )}
            {data.probe && (
              <span className={data.probe.leak_suspected ? "probe bad" : "probe ok"}
                    title={data.probe.rule}>
                記憶探測：{data.probe.leak_suspected ? "疑似記住歷史價格" : "未見記憶跡象"}
                （事前誤差 {fmt(data.probe.pre_cutoff?.median_abs_pct_error)}%／事後 {fmt(data.probe.post_cutoff?.median_abs_pct_error)}%）
              </span>
            )}
          </div>
          <div className="replay-legend">
            <span className="lg equity">策略權益（OOS）</span>
            <span className="lg benchmark">買進持有</span>
            <span className="lg dirty">污染區間</span>
            <span className="lg fold">fold 起點</span>
          </div>
          <ReplayChart data={data} cursor={card?.date} onPick={pickDay} />
          <div className="replay-controls">
            <button onClick={() => setAt((i) => Math.max(0, i - 1))} aria-label="上一個決策">◀</button>
            <button onClick={() => setPlaying((p) => !p)}>{playing ? "暫停" : "播放"}</button>
            <button onClick={() => setAt((i) => Math.min(decisions.length - 1, i + 1))} aria-label="下一個決策">▶</button>
            <input type="range" min={0} max={Math.max(0, decisions.length - 1)} value={at}
                   onChange={(e) => setAt(Number(e.target.value))} aria-label="決策日" />
            <span className="mono">{card?.date}</span>
          </div>
          {card && (
            <div className="replay-card">
              <section>
                <h3>決策 {card.date}{card.contaminated && <em className="badge dirty">污染・不計分</em>}</h3>
                {card.called ? (
                  <>
                    <p className="decision">
                      <b>{dirText[String(card.decision?.direction)] ?? "—"}</b>
                      ・信心 {fmt(card.decision?.confidence)}
                      ・{card.period_return == null ? "樣本內（未進入 OOS，不計績效）" : `持有期間 OOS 報酬 ${pct(card.period_return)}`}
                      {card.cached && <em className="badge">快取重播</em>}
                    </p>
                    <p className="rationale">{card.decision?.rationale}</p>
                  </>
                ) : (
                  <p className="muted">此決策日在模型知識截止前，未呼叫模型。</p>
                )}
                <h3>模型看到的特徵</h3>
                <Features features={card.features} />
                <h3>檢索到的研究（決策日前已公開）</h3>
                {card.docs.length ? (
                  <ul className="docs">
                    {card.docs.map((d) => <li key={d.id}><span className="mono">{d.knowledge_time}</span> {d.title}</li>)}
                  </ul>
                ) : <p className="muted">無</p>}
              </section>
              <section>
                <h3>推論過程（CoT）</h3>
                <pre className="cot">{card.reasoning || (card.called ? "（模型未回傳推論內容）" : "—")}</pre>
                {card.prompt && (
                  <details>
                    <summary>完整提示</summary>
                    <pre className="cot">{card.prompt}</pre>
                  </details>
                )}
                {card.content && (
                  <details>
                    <summary>模型原始回答</summary>
                    <pre className="cot">{card.content}</pre>
                  </details>
                )}
              </section>
            </div>
          )}
          {data.folds.length > 0 && (
            <details className="folds">
              <summary>各 fold 的樣本內選擇（只看樣本內，不看樣本外）</summary>
              <table className="replay-table">
                <thead><tr><th>fold</th><th>樣本內</th><th>樣本外</th><th>IS Sharpe（各門檻）</th><th>選中門檻</th><th>OOS Sharpe</th><th>OOS 報酬</th></tr></thead>
                <tbody>
                  {data.folds.map((f) => (
                    <tr key={f.fold}>
                      <td>{f.fold}</td><td className="mono">{f.train_start}→{f.train_end}</td>
                      <td className="mono">{f.test_start}→{f.test_end}</td>
                      <td className="mono">{Object.entries(f.is_sharpe).map(([k, v]) => `${k}:${fmt(v)}`).join("  ")}</td>
                      <td>{f.chosen_threshold}</td><td>{fmt(f.oos_sharpe)}</td><td>{pct(f.oos_return)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
          )}
        </>
      )}
    </div>
  );
}
