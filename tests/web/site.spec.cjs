const { test, expect } = require('@playwright/test');

async function load(page, path = './') {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(path);
  await expect(page.locator('html')).toHaveAttribute('data-ready', 'true');
  expect(errors).toEqual([]);
}

test('catalog, quick routes, search, details and clipboard work', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await load(page);
  await expect(page.locator('#source-title')).toHaveText('PDF 文档');
  await page.locator('.quick-route[data-source="glb"]').click();
  await expect(page.locator('#detail-title')).toHaveText('GLB → FBX 模型');
  await expect(page.locator('#command-text')).toContainText('--format fbx');
  await page.locator('#copy-command').click();
  await expect(page.locator('#copy-status')).toHaveText('命令已复制');
  expect(await page.evaluate(() => navigator.clipboard.readText())).toContain('--format fbx');
  await page.keyboard.press('Escape');
  await expect(page.locator('#route-detail')).toBeHidden();
  await page.keyboard.press('/');
  await expect(page.locator('#format-search')).toBeFocused();
  await page.locator('#format-search').fill('HEIC');
  await expect(page.locator('#source-title')).toHaveText('手机照片');
  await page.locator('.target-button[data-target="jpg"]').click();
  await expect(page.locator('#command-text')).toContainText('photo.heic');
  await page.locator('#format-search').fill('no-such-format');
  await expect(page.locator('#source-title')).toHaveText('未找到源格式');
  await expect(page.locator('#target-list button')).toHaveCount(0);
  await page.locator('#format-search').fill('');
  await expect(page.locator('#source-title')).toHaveText('PDF 文档');
  await expect(page.locator('.review-muted')).toHaveCount(0);
});

test('deep links, conditional routes and download are explicit', async ({ page, request }) => {
  await load(page, './?source=dxf&to=dwg');
  await expect(page.locator('#detail-note')).toContainText('尚未');
  await expect(page.locator('.target-button[data-target="dwg"]')).toContainText('尚未实测');
  const response = await request.get('./downloads/file-converter.zip');
  expect(response.ok()).toBeTruthy();
  const body = await response.body();
  expect(body.subarray(0, 2).toString()).toBe('PK');
  expect(body.length).toBeGreaterThan(20000);
});

test('catalog failure preserves honest feedback and download access', async ({ page }) => {
  await page.route('**/routes.json', route => route.fulfill({ status: 503, body: 'unavailable' }));
  await page.goto('./');
  await expect(page.locator('html')).toHaveAttribute('data-ready', 'error');
  await expect(page.locator('#source-list')).toContainText('读取失败');
  await expect(page.getByRole('link', { name: '下载 Skill' })).toBeVisible();
});

for (const width of [320, 390, 1440]) {
  test(`layout and route details fit ${width}px viewport`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await load(page, './?source=mp3&to=srt');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
    await expect(page.locator('#route-detail')).toBeVisible();
    await page.locator('#formats').scrollIntoViewIfNeeded();
    await page.screenshot({ path: `test-results/site-${width}.png`, fullPage: true });
  });
}

test('review navigation, replay, comparison, focus and scroll remain synchronized', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 950 });
  await load(page, './review/');
  const frame = page.frameLocator('#new-frame');
  await expect(page.locator('#step-number')).toHaveText('1 / 3');
  await expect(page.locator('#previous')).toBeDisabled();
  await page.locator('#next').click();
  await expect(page.locator('#step-number')).toHaveText('2 / 3');
  await expect(frame.locator('#detail-title')).toHaveText('GLB → FBX 模型');
  const opacity = await frame.locator('#formats').evaluate(element => {
    let value = 1;
    for (let node = element; node; node = node.parentElement) value *= Number(getComputedStyle(node).opacity);
    return value;
  });
  expect(opacity).toBe(1);
  await expect(frame.locator('.hero')).toHaveCSS('opacity', '0.2');
  await frame.locator('#format-search').fill('HEIC');
  await page.locator('#replay').click();
  await expect(frame.locator('#source-title')).toHaveText('3D 模型');
  await page.locator('#show-current').click();
  await expect(page.locator('#show-current')).toHaveAttribute('aria-pressed', 'true');
  await page.locator('#show-comparison').click();
  await expect(page.locator('#divider')).toBeVisible();
  await page.locator('#divider').focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.locator('#divider')).toHaveAttribute('aria-valuenow', '55');
  const box = await page.locator('#divider').boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + 100);
  await page.mouse.down();
  await page.mouse.move(400, 100);
  await page.mouse.up();
  expect(Number(await page.locator('#divider').getAttribute('aria-valuenow'))).toBeLessThan(40);
  const widths = await page.locator('iframe').evaluateAll(nodes => nodes.map(node => node.getBoundingClientRect().width));
  expect(widths).toEqual([1440, 1440]);
  await page.locator('#show-new').click();
  await page.locator('#next').click();
  await expect(page.locator('#step-number')).toHaveText('3 / 3');
  await expect(page.locator('#next')).toBeDisabled();
  await page.locator('#previous').click();
  await expect(page.locator('#step-number')).toHaveText('2 / 3');
  await expect.poll(() => page.evaluate(() => Math.abs(
    document.querySelector('#new-frame').contentWindow.scrollY - document.querySelector('#current-frame').contentWindow.scrollY
  ))).toBeLessThan(3);
  await page.screenshot({ path: 'test-results/review-desktop.png' });
});

test('review toolbar stays within mobile viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await load(page, './review/');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.locator('#next').click();
  await expect(page.locator('#step-number')).toHaveText('2 / 3');
  await expect(page.locator('#show-new')).toBeVisible();
  await page.screenshot({ path: 'test-results/review-mobile.png' });
});
