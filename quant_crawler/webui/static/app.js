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
  if (s.server_started) {
    $("#server-stamp").textContent =
      `server 啟動於 ${s.server_started} · code ${s.code_rev || "?"}（改碼後需重啟 server 才生效）`;
  }

  const kindc = s.papers_by_kind || { strategy: 0, factor: 0 };
  const cards = [
    { label: "論文/報告總量", value: s.papers_total, cls: "accent" },
    { label: "策略 / 因子", value: `${kindc.strategy}/${kindc.factor}`, cls: "" },
    { label: "已下載 PDF", value: s.pdfs_downloaded ?? 0, cls: "" },
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
let CURRENT_KIND = "strategy";
let TAXONOMY = { strategy: [], factor: [] };

async function loadTaxonomy() {
  try { TAXONOMY = await getJSON("/api/taxonomy"); } catch { /* keep empty */ }
}

function populateSubcatFilter() {
  const sel = $("#subcat-filter");
  const cur = sel.value;
  sel.replaceChildren(el("option", { value: "" }, "全部子類別"));
  for (const s of (TAXONOMY[CURRENT_KIND] || [])) {
    sel.append(el("option", { value: s }, s));
  }
  // keep selection if still valid
  if ([...sel.options].some((o) => o.value === cur)) sel.value = cur;
}

async function postLabel(source, source_id, op, value) {
  const r = await fetch("/api/labels", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source, source_id, op, value }),
  });
  if (!r.ok) {
    const e = await r.json().catch(() => ({}));
    throw new Error(e.error || `HTTP ${r.status}`);
  }
  return r.json();
}

function subcatChip(p, tag, manual) {
  const chip = el("span", { class: `tag ${manual ? "tag-manual" : ""}`, title: manual ? "手動標籤" : "自動分類" }, tag);
  if (manual) {
    const x = el("span", { class: "chip-x", title: "移除" }, " ×");
    x.addEventListener("click", async () => {
      try { await postLabel(p.source, p.source_id, "remove_subcat", tag); await loadPapers(); }
      catch (e) { showError(e.message); }
    });
    chip.append(x);
  }
  return chip;
}

function renderPaperRow(p) {
  // subcats cell: auto chips + manual chips + add control
  const subWrap = el("div", { class: "tags" });
  for (const t of p.subcats_auto || []) subWrap.append(subcatChip(p, t, false));
  for (const t of p.subcats_manual || []) subWrap.append(subcatChip(p, t, true));
  const addInput = el("input", { type: "text", class: "subcat-add", placeholder: "+標籤", list: "subcat-options" });
  addInput.addEventListener("keydown", async (ev) => {
    if (ev.key === "Enter" && addInput.value.trim()) {
      try { await postLabel(p.source, p.source_id, "add_subcat", addInput.value.trim()); await loadPapers(); }
      catch (e) { showError(e.message); }
    }
  });
  subWrap.append(addInput);

  // PDF / page links
  let pdfCell;
  if (p.pdf_local) {
    pdfCell = el("a", { href: `/files/pdf/${encodeURIComponent(p.pdf_local)}`, target: "_blank", rel: "noopener", title: p.pdf_local }, "📄本地");
  } else if (p.pdf_url) {
    pdfCell = el("a", { href: p.pdf_url, target: "_blank", rel: "noopener" }, "⬇遠端");
  } else { pdfCell = document.createTextNode("—"); }
  const links = el("span", {}, p.url ? el("a", { href: p.url, target: "_blank", rel: "noopener" }, "open") : "—", document.createTextNode(" · "), pdfCell);

  // kind override select
  const kindSel = el("select", { class: "kind-select", title: p.kind_overridden ? "已手動覆寫" : "自動分類" });
  for (const [v, label] of [["", "自動"], ["strategy", "strategy"], ["factor", "factor"]]) {
    const o = el("option", { value: v }, label);
    if ((v === "" && !p.kind_overridden) || (p.kind_overridden && v === p.kind)) o.selected = true;
    kindSel.append(o);
  }
  if (p.kind_overridden) kindSel.classList.add("overridden");
  kindSel.addEventListener("change", async () => {
    try { await postLabel(p.source, p.source_id, "set_kind", kindSel.value || null); await loadPapers(); }
    catch (e) { showError(e.message); }
  });

  return el("tr", {},
    el("td", { class: "mono" }, p.source),
    el("td", {}, p.title || "(無標題)"),
    el("td", {}, subWrap),
    el("td", {}, links),
    el("td", {}, kindSel),
  );
}

async function loadPapers() {
  const pdf = $("#papers-filter").value;       // "" | "any" | "local"
  const subcat = $("#subcat-filter").value;    // "" | <tag>
  const params = new URLSearchParams({ kind: CURRENT_KIND, limit: "500" });
  if (pdf) params.set("pdf", pdf);
  if (subcat) params.set("subcat", subcat);
  const data = await getJSON(`/api/papers?${params.toString()}`);
  const rows = data.papers;
  const kindLabel = CURRENT_KIND === "factor" ? "因子" : "策略";
  $("#papers-hint").textContent =
    `${kindLabel} ${rows.length} 筆` + (subcat ? ` · 子類別=${subcat}` : "") + (pdf ? ` · ${pdf === "local" ? "本地PDF" : "有PDF"}` : "");
  const tbody = $("#papers-table tbody");
  tbody.replaceChildren();
  $("#papers-empty").hidden = rows.length > 0;
  $("#papers-table").hidden = rows.length === 0;
  for (const p of rows) tbody.append(renderPaperRow(p));
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

function syncDatalist() {
  // autocomplete options for the manual-tag input = current kind's vocabulary
  let dl = $("#subcat-options");
  if (!dl) {
    dl = el("datalist", { id: "subcat-options" });
    document.body.append(dl);
  }
  dl.replaceChildren(...(TAXONOMY[CURRENT_KIND] || []).map((s) => el("option", { value: s })));
}

// ---------- orchestration ----------
async function refreshAll() {
  showError("");
  try {
    await loadSummary();
    await loadTaxonomy();
    populateSubcatFilter();
    syncDatalist();
    await loadDates();
    await loadRuns();
    await loadPapers();
    await loadStrategies();
  } catch (e) {
    showError(e.message || String(e));
  }
}

async function reloadPapersSafe() {
  showError("");
  try { await loadPapers(); } catch (e) { showError(e.message || String(e)); }
}

document.addEventListener("DOMContentLoaded", () => {
  $("#refresh-btn").addEventListener("click", refreshAll);
  $("#runs-date").addEventListener("change", async () => {
    showError("");
    try { await loadRuns(); } catch (e) { showError(e.message || String(e)); }
  });
  $("#strat-filter").addEventListener("input", (e) => renderStrategies(e.target.value));
  $("#papers-filter").addEventListener("change", reloadPapersSafe);
  $("#subcat-filter").addEventListener("change", reloadPapersSafe);
  // kind tabs
  for (const btn of $$("#kind-tabs .tab")) {
    btn.addEventListener("click", async () => {
      $$("#kind-tabs .tab").forEach((b) => b.classList.toggle("active", b === btn));
      CURRENT_KIND = btn.dataset.kind;
      $("#subcat-filter").value = "";
      populateSubcatFilter();
      syncDatalist();
      await reloadPapersSafe();
    });
  }
  refreshAll();
});
