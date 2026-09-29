import { describe, it, expect, vi, afterEach } from "vitest";
import { compatible, unavailable, estimateText, latestPreview } from "./model";
afterEach(() => vi.useRealTimers());
describe("typed ports", () => {
  it("only permits equal known types", () => {
    expect(compatible("Score", "Score")).toBe(true);
    expect(compatible("Sigma", "Score")).toBe(false);
    expect(compatible(undefined, undefined)).toBe(false);
  });
});
it("missing Sigma marks sizing and its downstream unavailable", () => {
  const graph = {
    nodes: [
      { id: "sizing", type: "size" },
      { id: "backtest", type: "bt" },
      { id: "report", type: "report" },
    ],
    edges: [
      { from: ["sizing", "Weights"], to: ["backtest", "Weights"] },
      { from: ["backtest", "Returns"], to: ["report", "Returns"] },
    ],
  };
  const m = unavailable(graph, {
    size: { inputs: { Sigma: "Sigma" } },
    bt: { inputs: { Weights: "Weights" } },
    report: { inputs: { Returns: "Returns" } },
  });
  expect(m.sizing).toBe("缺 Sigma");
  expect(m.backtest).toContain("缺 Sigma");
  expect(m.report).toContain("缺 Sigma");
});
describe("N estimate", () => {
  it("shows new configuration increment and replay unchanged", () => {
    expect(
      estimateText({
        selection_n: 34,
        next_selection_n: 35,
        already_recorded: false,
      }),
    ).toBe("執行・N 34→35");
    expect(estimateText({ already_recorded: true })).toBe(
      "執行・快取重播，N 不變",
    );
  });
});
describe("latest preview scheduler", () => {
  it("immediately cancels a running preview on a new edit and applies the newest payload after it ends", async () => {
    vi.useFakeTimers();
    let end;
    let running = false;
    const cancel = vi.fn(async () => {
      if (running) {
        running = false;
        end();
      }
    });
    const apply = vi.fn();
    const preview = vi
      .fn()
      .mockImplementationOnce(() => {
        running = true;
        return new Promise((r) => (end = r));
      })
      .mockResolvedValue();
    const q = latestPreview({ cancel, apply, preview });
    q.schedule("momentum", "lookback", 10);
    await vi.advanceTimersByTimeAsync(300);
    expect(running).toBe(true);
    q.schedule("momentum", "lookback", 20);
    expect(cancel).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(300);
    expect(apply).toHaveBeenLastCalledWith({ momentum: { lookback: 20 } });
    expect(preview).toHaveBeenCalledTimes(2);
    q.dispose();
  });
  it("marks the initial pending preview busy before its debounce fires", () => {
    vi.useFakeTimers();
    const onState = vi.fn();
    const q = latestPreview({
      cancel: vi.fn(),
      apply: vi.fn(),
      preview: vi.fn(),
      onState,
    });
    q.start();
    expect(q.pending).toBe(true);
    expect(onState).toHaveBeenCalledWith("debouncing");
    q.dispose();
  });
  it("debounces rapid edits and cancels before applying only latest value", async () => {
    vi.useFakeTimers();
    const calls = [];
    const q = latestPreview({
      cancel: async () => calls.push("cancel"),
      apply: async (x) => calls.push(x),
      preview: async () => calls.push("preview"),
    });
    q.schedule("momentum", "lookback", 10);
    await vi.advanceTimersByTimeAsync(200);
    q.schedule("momentum", "lookback", 20);
    await vi.advanceTimersByTimeAsync(299);
    expect(calls).toEqual([]);
    await vi.advanceTimersByTimeAsync(1);
    expect(calls).toEqual([
      "cancel",
      { momentum: { lookback: 20 } },
      "preview",
    ]);
    q.dispose();
  });
  it("waits for cancellation and suppresses obsolete preview without parallel jobs", async () => {
    vi.useFakeTimers();
    let release;
    const preview = vi.fn(),
      apply = vi.fn();
    const cancel = vi
      .fn()
      .mockImplementationOnce(() => new Promise((r) => (release = r)))
      .mockResolvedValue();
    const q = latestPreview({ cancel, apply, preview });
    q.schedule("momentum", "lookback", 10);
    await vi.advanceTimersByTimeAsync(300);
    q.schedule("momentum", "lookback", 30);
    release();
    await vi.advanceTimersByTimeAsync(0);
    expect(preview).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(300);
    expect(preview).toHaveBeenCalledTimes(1);
    expect(apply).toHaveBeenLastCalledWith({ momentum: { lookback: 30 } });
    q.dispose();
  });
});
