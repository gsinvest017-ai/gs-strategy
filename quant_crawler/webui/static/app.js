"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url} -> HTTP ${r.status}`);
  return r.json();
}

function showError(msg) {
  $("#err-banner").textContent = msg ? `⚠ ${msg}` : "";
}

function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else node.setAttribute(k, v);
  }
  for (const c of children) {
    if (c == null) continue;
    node.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return node;
}

// ---------- summary cards + source bars ----------
async function loadSummary() {
  const s = await getJSON("/api/summary");
  $("#generated-at").textContent = `更新於 ${s.generated_at} · 今日 ${s.today}`;
  $("#export-dir-hint").textContent = `匯出目標：${s.export_dir}`;

  const cards = [
    { label: "論文/報告總量", value: s.papers_total, cls: "accent" },
    { label: "今日 routine", value: s.runs_today, cls: "" },
    { label: "策略總數", value: s.strategies_total,
      sub: `${s.strategies_manual} 手寫 / ${s.strategies_generated} 自動`, cls: "" },
    { label: "已匯出", value: s.strategies_exported, cls: "green" },
    { label: "待匯出", value: s.strategies_pending, cls: "amber" },
  ];
  const wrap = $("#cards");
  wrap.replaceChildren();
  for (const c of cards) {
    wrap.append(el("div", { class: `card ${c.cls}` },
      el("div", { class: "label" }, c.label),
      el("div", { class: "value" },
        String(c.value),
        c.sub ? el("small", {}, ` ${c.sub}`) : null),
    ));
  }

  // source bars
  const bars = $("#source-bars");
  bars.replaceChildren();
  const max = Math.max(1, ...s.papers_by_source.map((x) => x.count));
  for (const row of s.papers_by_source) {
    bars.append(el("div", { class: "bar-row" },
      el("span", { class: "name" }, row.source),
      el("div", { class: "bar-track" },
        el("div", { class: "bar-fill", style: `width:${(row.count / max) * 100}%` })),
      el("span", { class: "n" }, String(row.count)),
    ));
  }
}

// ---------- crawl runs ----------
async function loadDates() {
  const { dates } = await getJSON("/api/dates");
  const sel = $("#runs-date");
  sel.replaceChildren();
  const today = new Date().toISOString().slice(0, 10);
  const opts = dates.length ? dates : [today];
  if (!opts.includes(today)) opts.unshift(today);
  for (const d of opts) sel.append(el("option", { value: d }, d));
  sel.value = opts.includes(today) ? today : opts[0];
}

async function loadRuns() {
  const date = $("#runs-date").value;
  const { runs } = await getJSON(`/api/runs?date=${encodeURIComponent(date)}`);
  const tbody = $("#runs-table tbody");
  tbody.replaceChildren();
  $("#runs-empty").hidden = runs.length > 0;
  $("#runs-table").hidden = runs.length === 0;
  for (const r of runs) {
    let badge;
    if (r.error) badge = el("span", { class: "badge err" }, "錯誤");
    else if (!r.finished_at) badge = el("span", { class: "badge review" }, "進行中");
    else badge = el("span", { class: "badge ok" }, "成功");
    tbody.append(el("tr", {},
      el("td", { class: "mono" }, r.source),
      el("td", { class: "mono" }, (r.started_at || "").replace("T", " ").replace("Z", "")),
      el("td", { class: "mono" }, (r.finished_at || "—").replace("T", " ").replace("Z", "")),
      el("td", { class: "mono" }, String(r.items_seen)),
      el("td", { class: "mono" }, String(r.items_kept)),
      el("td", {}, badge),
    ));
  }
}

// ---------- new papers ----------
async function loadPapers() {
  const date = $("#runs-date").value;
  const data = await getJSON(`/api/papers?date=${encodeURIComponent(date)}&limit=100`);
  let rows = data.papers;
  let hint = `${date} 新增 ${rows.length} 筆`;
  // If the picked date has no fetched papers, show latest as a fallback view.
  if (rows.length === 0) {
    const latest = await getJSON(`/api/papers?limit=15`);
    rows = latest.papers;
    hint = latest.fallback_latest
      ? `（${date} 無新增；顯示最近 ${rows.length} 筆）`
      : hint;
  }
  $("#papers-hint").textContent = hint;
  const tbody = $("#papers-table tbody");
  tbody.replaceChildren();
  $("#papers-empty").hidden = rows.length > 0;
  $("#papers-table").hidden = rows.length === 0;
  for (const p of rows) {
    // PDF link: prefer the locally-downloaded file, else the remote pdf_url.
    let pdfCell;
    if (p.pdf_local) {
      pdfCell = el("a", { href: `/files/pdf/${encodeURIComponent(p.pdf_local)}`,
                          target: "_blank", rel: "noopener", title: p.pdf_local },
                   "📄 本地");
    } else if (p.pdf_url) {
      pdfCell = el("a", { href: p.pdf_url, target: "_blank", rel: "noopener" }, "⬇ 遠端");
    } else {
      pdfCell = document.createTextNode("—");
    }
    tbody.append(el("tr", {},
      el("td", { class: "mono" }, p.source),
      el("td", {}, p.title || "(無標題)"),
      el("td", { class: "mono" }, p.published || "—"),
      el("td", {}, p.url ? el("a", { href: p.url, target: "_blank", rel: "noopener" }, "open") : "—"),
      el("td", {}, pdfCell),
    ));
  }
}

// ---------- strategies ----------
let STRATEGIES = [];

function renderStrategies(filter = "") {
  const q = filter.trim().toLowerCase();
  const tbody = $("#strat-table tbody");
  tbody.replaceChildren();
  const rows = STRATEGIES.filter((s) => {
    if (!q) return true;
    const hay = [s.id, s.template, s.origin, ...(s.tags || [])].join(" ").toLowerCase();
    return q.split(/\s+/).every((tok) => hay.includes(tok));
  });
  $("#strat-empty").hidden = rows.length > 0;
  $("#strat-table").hidden = rows.length === 0;
  for (const s of rows) {
    const tags = el("div", { class: "tags" });
    for (const t of (s.tags || [])) tags.append(el("span", { class: "tag" }, t));
    const exported = s.exported
      ? el("span", { class: "badge ok" }, "✓ 已匯出")
      : el("span", { class: "badge no" }, "未匯出");
    const review = s.requires_review
      ? el("span", { class: "badge review" }, "待審")
      : el("span", { class: "badge no" }, "—");
    // spec links: README.md (the human spec) + manifest.yaml
    const specCell = el("span", { class: "spec-links" });
    if (s.has_spec_md) {
      specCell.append(el("a", {
        href: `/files/strategy/${encodeURIComponent(s.id)}/README.md`,
        target: "_blank", rel: "noopener", title: "策略 spec markdown",
      }, "📑 spec"));
    }
    if ((s.spec_files || []).includes("manifest.yaml")) {
      if (specCell.childNodes.length) specCell.append(document.createTextNode(" · "));
      specCell.append(el("a", {
        href: `/files/strategy/${encodeURIComponent(s.id)}/manifest.yaml`,
        target: "_blank", rel: "noopener", title: "manifest.yaml",
      }, "manifest"));
    }
    if (!specCell.childNodes.length) specCell.append(document.createTextNode("—"));
    tbody.append(el("tr", {},
      el("td", { class: "mono" }, s.id),
      el("td", {}, el("span", { class: `badge ${s.origin}` }, s.origin)),
      el("td", { class: "mono" }, s.template || "—"),
      el("td", {}, tags),
      el("td", {}, specCell),
      el("td", {}, review),
      el("td", {}, exported),
    ));
  }
}

async function loadStrategies() {
  const { strategies } = await getJSON("/api/strategies");
  STRATEGIES = strategies;
  renderStrategies($("#strat-filter").value);
}

// ---------- orchestration ----------
async function refreshAll() {
  showError("");
  try {
    await loadSummary();
    await loadDates();
    await loadRuns();
    await loadPapers();
    await loadStrategies();
  } catch (e) {
    showError(e.message || String(e));
  }
}

document.addEventListener("DOMContentLoaded", () => {
  $("#refresh-btn").addEventListener("click", refreshAll);
  $("#runs-date").addEventListener("change", async () => {
    showError("");
    try { await loadRuns(); await loadPapers(); }
    catch (e) { showError(e.message || String(e)); }
  });
  $("#strat-filter").addEventListener("input", (e) => renderStrategies(e.target.value));
  refreshAll();
});
