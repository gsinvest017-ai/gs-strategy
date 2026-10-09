import React from "react";
import { renderToString } from "react-dom/server";
import { expect, it } from "vitest";
import { Confidential, JobStatus, MAX_SUBMISSION_BYTES, validateSubmission } from "./Confidential";

const example = () => ({ header: {
  schema: "straty-submission/1", subject: "qr", submission_id: "a".repeat(32), owner_key_id: "owner",
  broker_key_id: "broker", recipient_key_id: "recipient", recipient_fingerprint: "a".repeat(64),
  dataset_id: "fixture", dataset_sha256: "a".repeat(64), engine_sha256: "a".repeat(64),
  config_sha256: "a".repeat(64), seed: 0, issued_at: 1, expires_at: 2,
}, envelope: { version: "straty-envelope/1", ephemeral_public_key: "public", nonce: "nonce", ciphertext: "encrypted" }, signature: "signed" });

it("preserves signed JSON bytes including unsigned 64-bit seed", () => {
  const raw = JSON.stringify(example()).replace('"seed":0', '"seed":18446744073709551615');
  expect(validateSubmission(raw)).toBe(raw);
});
it.each(["source", "private_key", "config"])("rejects plaintext extra field %s", (key) => {
  const body = example(); body[key] = "sensitive";
  expect(() => validateSubmission(JSON.stringify(body))).toThrow();
  delete body[key]; body.header[key] = "sensitive";
  expect(() => validateSubmission(JSON.stringify(body))).toThrow();
});
it("rejects oversized or unencrypted uploads", () => {
  expect(() => validateSubmission(" ".repeat(MAX_SUBMISSION_BYTES + 1))).toThrow();
  expect(() => validateSubmission('{"source":"def decide(history): return 1"}')).toThrow();
});
it("keeps execution, accounting validation and encrypted delivery distinct", () => {
  const html = renderToString(React.createElement(JobStatus, {job: { id: "a".repeat(32), execution: "succeeded", verification: "passed", delivery: "available" }}));
  expect(html).toContain("執行完成");
  expect(html).toContain("帳務與輸入契約通過");
  expect(html).toContain("密文可下載");
  expect(html).toContain("策略研究資格尚未評估");
  expect(html).not.toContain("策略合格");
  expect(html).not.toContain("已收妥");
});
it("initial panel offers no plaintext or private key input", () => {
  const html = renderToString(React.createElement(Confidential, {close: () => {}}));
  expect(html).toContain("此面板不接收策略原始碼或私鑰");
  expect(html).not.toContain("textarea");
});
