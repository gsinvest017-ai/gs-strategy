import React, { useEffect, useRef, useState } from "react";
import { api, sessionHeaders } from "./model";
import "./Confidential.css";

export const MAX_SUBMISSION_BYTES = 1000000;
const exact = (value, keys) => value && typeof value === "object" && !Array.isArray(value)
  && Object.keys(value).sort().join(",") === [...keys].sort().join(",");
const headerKeys = ["schema", "subject", "submission_id", "owner_key_id", "broker_key_id",
  "recipient_key_id", "recipient_fingerprint", "dataset_id", "dataset_sha256", "engine_sha256",
  "config_sha256", "seed", "issued_at", "expires_at"];

export function validateSubmission(text) {
  if (typeof text !== "string" || new TextEncoder().encode(text).length > MAX_SUBMISSION_BYTES)
    throw new Error("invalid submission");
  const data = JSON.parse(text);
  if (!exact(data, ["header", "envelope", "signature"])
    || !exact(data.header, headerKeys) || data.header.schema !== "straty-submission/1"
    || !headerKeys.filter((key) => !["seed", "issued_at", "expires_at"].includes(key))
      .every((key) => typeof data.header[key] === "string")
    || !["seed", "issued_at", "expires_at"].every((key) => typeof data.header[key] === "number")
    || !exact(data.envelope, ["version", "ephemeral_public_key", "nonce", "ciphertext"])
    || data.envelope.version !== "straty-envelope/1"
    || ![data.envelope.ephemeral_public_key, data.envelope.nonce, data.envelope.ciphertext, data.signature]
      .every((value) => typeof value === "string" && value.length > 0)) throw new Error("invalid submission");
  // Preserve original bytes: parsing/re-stringifying would round unsigned 64-bit seeds.
  return text;
}

export function statusText(kind, value) {
  const labels = {
    execution: { accepted: "已受理", running: "執行中", succeeded: "執行完成", failed: "執行失敗", interrupted: "執行中斷" },
    verification: { passed: "帳務與輸入契約通過", failed: "帳務或輸入契約未通過", not_run: "尚未驗證" },
    delivery: { available: "密文可下載", not_ready: "密文尚未備妥" },
  };
  return labels[kind]?.[value] || "尚無狀態";
}

export function JobStatus({ job }) {
  return <section className="confidential-status" aria-label="機密工作狀態">
    <p>工作識別：<span className="mono">{job.id}</span></p>
    <dl>{[["execution", "執行"], ["verification", "驗證"], ["delivery", "交付"]].map(([key, label]) =>
      <div key={key}><dt>{label}</dt><dd>{statusText(key, job[key])}</dd></div>)}</dl>
    <p className="confidential-note">策略研究資格尚未評估。請在自己的可信裝置驗證收據與解密結果。</p>
  </section>;
}

export function Confidential({ close }) {
  const [availability, setAvailability] = useState("loading");
  const [file, setFile] = useState(null);
  const [job, setJob] = useState(null);
  const [jobId, setJobId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    fetch("/api/confidential/capabilities", { headers: sessionHeaders() }).then(async (response) => {
      if ([401, 403, 404].includes(response.status)) {
        if (mounted.current) setAvailability("disabled");
        return;
      }
      if (!response.ok) throw new Error("unavailable");
      await response.json();
      if (mounted.current) setAvailability("enabled");
    }).catch(() => {
      if (mounted.current) setAvailability("error");
    });
    return () => { mounted.current = false; };
  }, []);

  async function action(fn) {
    setBusy(true); setError("");
    try { await fn(); }
    catch { if (mounted.current) setError("操作未完成，請確認檔案、工作識別與存取權限後重試。"); }
    finally { if (mounted.current) setBusy(false); }
  }
  function retain(next) {
    if (mounted.current) { setJob(next); setJobId(next.id); }
  }
  const lookup = () => action(async () => {
    if (!/^[a-f0-9]{32}$/.test(jobId)) throw new Error("invalid id");
    retain(await api(`/confidential/jobs/${jobId}`));
  });
  const submit = () => action(async () => {
    if (!file || file.size > MAX_SUBMISSION_BYTES) throw new Error("invalid file");
    const raw = validateSubmission(await file.text());
    const response = await fetch("/api/confidential/jobs", {
      method: "POST", headers: { "Content-Type": "application/json", ...sessionHeaders() }, body: raw,
    });
    if (!response.ok) throw new Error("submission failed");
    retain(await response.json());
    if (mounted.current) setFile(null);
  });
  const download = () => action(async () => {
    const response = await fetch(`/api/confidential/jobs/${encodeURIComponent(job.id)}/result`, { headers: sessionHeaders() });
    if (!response.ok) throw new Error("result unavailable");
    const raw = await response.text();
    const result = JSON.parse(raw);
    if (!exact(result, ["binding", "envelope", "receipt", "signature"])
      || !exact(result.envelope, ["version", "ephemeral_public_key", "nonce", "ciphertext"])
      || result.envelope.version !== "straty-envelope/1") throw new Error("invalid ciphertext result");
    if (!mounted.current) return;
    const url = URL.createObjectURL(new Blob([raw], { type: "application/json" }));
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = `straty-${job.id}-encrypted-result.json`;
    document.body.appendChild(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });

  return <div className="replay-overlay confidential-overlay" role="dialog" aria-modal="true" aria-label="機密回測">
    <header><div><small>CONFIDENTIAL BACKTEST</small><h2>機密回測</h2></div><button onClick={close}>關閉</button></header>
    <p>在可信裝置封裝並簽署策略後，上傳已加密 JSON。此面板不接收策略原始碼或私鑰。</p>
    {availability === "loading" && <p role="status">正在確認服務狀態…</p>}
    {availability === "disabled" && <p role="status">此帳號尚未啟用機密回測。</p>}
    {availability === "error" && <p role="alert">目前無法確認服務狀態，請關閉後重試。</p>}
    {availability === "enabled" && <>
      <section className="confidential-input"><label htmlFor="confidential-upload">已加密且簽署的工作檔案（上限 1 MB）</label>
        <input id="confidential-upload" type="file" accept="application/json,.json" disabled={busy}
          onChange={(event) => { setFile(event.target.files?.[0] || null); setError(""); }} />
        <button disabled={busy || !file} onClick={submit}>提交機密工作</button>
      </section>
      <section className="confidential-input"><label htmlFor="confidential-job">工作識別</label>
        <input id="confidential-job" value={jobId} maxLength={32} disabled={busy} autoComplete="off"
          onChange={(event) => setJobId(event.target.value.trim())} placeholder="輸入工作識別，或提交新工作" />
        <button disabled={busy || !jobId} onClick={lookup}>更新工作狀態</button>
      </section>
      {job && <><JobStatus job={job} /><button disabled={busy || job.delivery !== "available"} onClick={download}>下載加密結果</button></>}
      {busy && <p role="status">正在處理…</p>}
      {error && <p role="alert">{error}</p>}
    </>}
  </div>;
}
