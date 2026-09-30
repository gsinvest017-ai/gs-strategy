const { test: base, expect } = require('../../strategies/_common/graph/ui/node_modules/@playwright/test');
const path = require('node:path');
const os = require('node:os');

// Every scenario uses a real isolated server. Observe requests without mocking APIs.
const test = base.extend({
  page: async ({ page }, use) => {
    const external = [];
    const errors = [];
    page.on('request', request => {
      if (new URL(request.url()).origin !== 'http://127.0.0.1:19102') external.push('external request');
    });
    page.on('pageerror', () => errors.push('browser error'));
    page.on('console', message => {
      if (message.type() === 'error' && /content security policy|maximum update depth/i.test(message.text())) {
        errors.push('resource policy or rendering error');
      }
    });
    await use(page);
    expect(external, 'runtime must only contact its loopback origin').toEqual([]);
    expect(errors, 'browser must not raise uncaught errors').toEqual([]);
  },
});

async function api(page, endpoint) {
  const response = await page.request.get(`/api/${endpoint}`);
  expect(response.ok()).toBeTruthy();
  return response.json();
}

async function idle(page) {
  await expect(page.getByTestId('preview-state')).toHaveText('idle');
  await expect(page.getByTestId('run')).toBeEnabled();
}

async function slide(page, value) {
  const slider = page.getByTestId('slider-momentum-lookback');
  const box = await slider.boundingBox();
  expect(box).not.toBeNull();
  const min = Number(await slider.getAttribute('min'));
  const max = Number(await slider.getAttribute('max'));
  const old = Number(await slider.inputValue());
  const point = v => box.x + 7 + ((v - min) / (max - min)) * (box.width - 14);
  await page.mouse.move(point(old), box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(point(value), box.y + box.height / 2, { steps: 12 });
  await page.mouse.up();
  await expect.poll(() => slider.inputValue()).not.toBe(String(old));
  await idle(page);
}

async function assertOverview(page) {
  await expect(page.getByText('上游預覽區・不計 N', { exact: true })).toBeVisible();
  await expect(page.getByText('試驗區・每個新組態 N+1', { exact: true })).toBeVisible();
  await expect.poll(async () => page.locator('.node-card').evaluateAll(cards => {
    const top = document.querySelector('.topbar').getBoundingClientRect().bottom;
    const bottom = document.querySelector('footer').getBoundingClientRect().top;
    const boxes = cards.map(card => card.getBoundingClientRect());
    const contained = boxes.every(b => b.x >= -1 && b.right <= innerWidth + 1 && b.y >= top - 1 && b.bottom <= bottom + 1);
    const overlap = boxes.some((a, i) => boxes.slice(i + 1).some(b =>
      Math.min(a.right, b.right) - Math.max(a.left, b.left) > 1 &&
      Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 1));
    return { count: boxes.length, contained, overlap };
  })).toEqual({ count: 13, contained: true, overlap: false });
}

// Reload while the first cold preview is executing against the real fixture.
test('refresh during active preview adopts the job and recovers automatically', async ({ page }) => {
  const failures = [];
  page.on('response', response => {
    if (response.url().includes('/api/') && response.status() >= 400) failures.push(response.status());
  });
  await page.goto('/');
  await expect.poll(async () => (await api(page, 'nodes/continuous')).status).toBe('running');
  await page.reload();
  await expect(page.locator('.error-banner')).toHaveCount(0);
  await expect(page.getByTestId('cancel')).toBeEnabled();
  await idle(page);
  await expect(page.getByTestId('node-continuous')).toHaveAttribute('data-status', /cached|recomputed/);
  await expect(page.getByTestId('node-momentum')).toHaveAttribute('data-status', /cached|recomputed/);
  await expect(page.locator('.error-banner')).toHaveCount(0);
  await expect(page.getByTestId('node-cost')).toContainText('TX 200・MTX 100 元／口，滑價 6 點');
  expect(failures).toEqual([]);
  expect((await api(page, 'ledger')).selection_n).toBe(0);
});

test.describe.serial('Live Strategy Graph fixture acceptance', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await expect(page.getByTestId('fixture-banner')).toHaveText('FIXTURE 資料・獨立 ledger');
    await idle(page);
  });

  test('Sigma → Score rejects the actual drag and preserves graph hash', async ({ page }) => {
    const before = await api(page, 'graph');
    const from = page.getByTestId('handle-volatility-output-Sigma');
    const to = page.getByTestId('handle-direction-input-Score');
    const a = await from.boundingBox();
    const b = await to.boundingBox();
    await page.mouse.move(a.x + a.width / 2, a.y + a.height / 2);
    await page.mouse.down();
    await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2, { steps: 18 });
    await expect(page.getByTestId('connection-error')).toContainText('型別不符：Sigma → Score');
    await page.mouse.up();
    expect((await api(page, 'graph')).graph_hash).toBe(before.graph_hash);
    expect((await api(page, 'graph')).graph.edges).toEqual(before.graph.edges);
  });

  test('lookback slider refreshes upstream preview without any backtest or N', async ({ page }) => {
    const before = await api(page, 'nodes/momentum');
    const ledger = await api(page, 'ledger');
    let runs = 0;
    let previews = 0;
    page.on('request', request => {
      if (request.method() === 'POST' && request.url().endsWith('/api/run')) runs += 1;
      if (request.method() === 'POST' && request.url().endsWith('/api/preview')) previews += 1;
    });
    await slide(page, 150);
    await expect.poll(async () => (await api(page, 'nodes/momentum')).hash).not.toBe(before.hash);
    expect(previews).toBeGreaterThan(0);
    expect(runs).toBe(0);
    expect((await api(page, 'ledger')).selection_n).toBe(ledger.selection_n);
    expect((await api(page, 'nodes/backtest')).outputs).toEqual({});
    await expect(page.getByTestId('node-backtest')).toContainText('過期');
  });

  test('new run adds one N, renders results, and replay keeps N unchanged', async ({ page }) => {
    const ledger = await api(page, 'ledger');
    await expect(page.getByTestId('estimate')).toContainText(`${ledger.selection_n}→${ledger.selection_n + 1}`);
    await page.getByTestId('run').click();
    await expect.poll(async () => (await api(page, 'ledger')).selection_n).toBe(ledger.selection_n + 1);
    await idle(page);
    await expect(page.getByTestId('selection-n')).toHaveText(String(ledger.selection_n + 1));
    await expect(page.getByTestId('node-report')).toContainText('Sharpe');
    await expect(page.getByTestId('node-facts')).toContainText('Jarque-Bera');
    await expect(page.getByTestId('node-resolve')).toContainText('threshold');
    expect((await api(page, 'nodes/report')).outputs.Report).toBeTruthy();
    expect((await api(page, 'nodes/facts')).outputs.Facts.provenance.normal.p_value).not.toBeNull();
    expect(Object.keys((await api(page, 'nodes/resolve')).outputs.Prescription.slots)).toHaveLength(5);
    await expect(page.getByTestId('estimate')).toContainText('快取重播，N 不變');
    await page.getByTestId('run').click();
    await idle(page);
    await expect.poll(async () => (await api(page, 'nodes/backtest')).status).toBe('cached');
    expect((await api(page, 'ledger')).selection_n).toBe(ledger.selection_n + 1);
    await page.getByRole('button', { name: '全圖', exact: true }).click();
    await assertOverview(page);
    await page.screenshot({ path: path.join(os.tmpdir(), 'live-strategy-graph-fixture-1280x800.png') });
  });

  test('cancelling actual backtest leaves stale results and unchanged N', async ({ page }) => {
    await slide(page, 190);
    const ledger = await api(page, 'ledger');
    await page.getByTestId('run').click();
    await expect.poll(async () => (await api(page, 'nodes/backtest')).status).toBe('running');
    await page.getByTestId('cancel').click();
    await idle(page);
    expect((await api(page, 'ledger')).selection_n).toBe(ledger.selection_n);
    await expect(page.getByTestId('node-backtest')).toContainText('過期');
  });

  test('moving a node persists layout without dirty/hash/N estimate changes', async ({ page }) => {
    await page.getByRole('button', { name: '存檔', exact: true }).click();
    await expect(page.getByTestId('dirty')).toHaveCount(0);
    const graph = await api(page, 'graph');
    const estimate = await api(page, 'run-estimate');
    const initialLayout = await api(page, 'layout');
    const title = page.getByTestId('node-momentum').locator('.node-title');
    const box = await title.boundingBox();
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width / 2 + 24, box.y + box.height / 2 + 16, { steps: 12 });
    await page.mouse.up();
    await expect.poll(async () => (await api(page, 'layout')).positions.momentum).not.toEqual(initialLayout.positions.momentum);
    await expect(page.getByTestId('dirty')).toHaveCount(0);
    expect((await api(page, 'graph')).graph_hash).toBe(graph.graph_hash);
    expect(await api(page, 'run-estimate')).toEqual(estimate);
  });

  test('parameter edits retain stale old results without running', async ({ page }) => {
    const ledger = await api(page, 'ledger');
    const previous = (await api(page, 'nodes/backtest')).outputs;
    await slide(page, 230);
    await expect(page.getByTestId('dirty')).toBeVisible();
    for (const id of ['backtest', 'report', 'facts', 'resolve']) {
      await expect(page.getByTestId(`node-${id}`)).toContainText('過期：顯示的是舊參數的結果');
    }
    expect((await api(page, 'nodes/backtest')).outputs).toEqual(previous);
    expect((await api(page, 'ledger')).selection_n).toBe(ledger.selection_n);
  });

  test('sidecar restores exact parameters and inspector exposes full chart and paged values', async ({ page }) => {
    let artifact;
    page.on('response', async response => {
      if (/\/api\/jobs\/[^/]+$/.test(response.url()) && response.ok()) {
        const job = await response.json();
        if (job.status === 'complete' && job.sidecar) artifact = job;
      }
    });
    await page.getByTestId('run').click();
    await expect.poll(() => Boolean(artifact)).toBe(true);
    await idle(page);
    const completed = await api(page, 'graph');
    await slide(page, 280);
    await page.getByRole('button', { name: '從產出載入', exact: true }).click();
    await page.locator('.loadbar input').fill(artifact.sidecar);
    await page.getByRole('button', { name: '載入圖快照', exact: true }).click();
    await idle(page);
    const restored = await api(page, 'graph');
    expect(restored.graph_hash).toBe(artifact.graph_hash);
    expect(restored.graph.nodes.find(n => n.id === 'momentum').params)
      .toEqual(completed.graph.nodes.find(n => n.id === 'momentum').params);
    await page.getByTestId('run').click();
    await idle(page);
    await page.getByRole('button', { name: '全圖', exact: true }).click();
    const viewport = page.locator('.react-flow__viewport');
    const transform = await viewport.getAttribute('style');
    await page.getByTestId('node-backtest').locator('.node-title').click();
    const drawer = page.locator('.drawer');
    await expect(drawer).toBeVisible();
    await expect(drawer.locator('tbody tr')).toHaveCount(60);
    await expect(viewport).toHaveAttribute('style', transform);
    await expect.poll(async () => (await drawer.locator('polyline').first().getAttribute('points')).split(' ').length).toBeGreaterThan(60);
    const chart = await drawer.locator('svg').boundingBox();
    await page.mouse.move(chart.x + chart.width / 2, chart.y + chart.height / 2);
    await expect(drawer.locator('.tooltip')).toBeVisible();
    await drawer.getByRole('button', { name: '較舊 60 筆' }).click();
    await expect(drawer.locator('nav')).toContainText('offset 60');
    await expect(drawer).toContainText('Provenance');
    await page.getByRole('button', { name: '關閉檢視' }).click();
  });

  test('underdetermined prescription shows the original remedy without an old prescription or extra N', async ({ page }) => {
    const ledger = await api(page, 'ledger');
    await page.getByTestId('param-facts-overlap').selectOption('clustered');
    await idle(page);
    await page.getByTestId('run').click();
    await idle(page);
    const resolver = await api(page, 'nodes/resolve');
    expect(resolver.status).toBe('error');
    await expect(page.getByTestId('node-resolve')).toHaveAttribute('data-status', 'error');
    await expect(page.getByTestId('node-resolve')).toContainText(resolver.message);
    await expect(page.getByTestId('node-resolve').locator('.prescription')).toHaveCount(0);
    await expect(page.getByTestId('node-report')).toContainText('Sharpe');
    expect((await api(page, 'nodes/report')).status).not.toBe('error');
    expect((await api(page, 'ledger')).selection_n).toBe(ledger.selection_n);
  });
});
