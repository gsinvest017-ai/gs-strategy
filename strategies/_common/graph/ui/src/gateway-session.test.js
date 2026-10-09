import { describe, it, expect, vi, afterEach } from "vitest";
import { sessionHeaders, api } from "./model";

afterEach(() => vi.unstubAllGlobals());
describe("origin-scoped gateway session proof", () => {
  it("leaves direct and existing OIDC modes compatible", () => {
    vi.stubGlobal("sessionStorage", undefined);
    expect(sessionHeaders()).toEqual({});
  });
  it("attaches proof to both read and write API requests", async () => {
    vi.stubGlobal("sessionStorage", { getItem: (key) => key === "straty_session_proof" ? "test-proof" : null });
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetch);
    await api("/session");
    await api("/graph", {});
    for (const [, options] of fetch.mock.calls)
      expect(options.headers["X-Straty-Session-Proof"]).toBe("test-proof");
  });
});
