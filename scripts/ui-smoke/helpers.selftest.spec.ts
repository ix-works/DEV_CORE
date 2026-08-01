/**
 * helpers.selftest.spec.ts — P/N kanıtları (radar 2026-08-01 ADOPT-4).
 * Koşum: npx playwright test helpers.selftest --config selftest.config.ts
 * T1: keşif ≥2 sayfa + dead-link kaydı + consoleErrors boş (P)
 * T2: file:// kapsam-filtresi — DİZİN DIŞI link keşfedilmez (pilot BLOCKER-A'nın testi) (N)
 * T3: aynı sayfa iki screenshot → pct < 0.02 (N)
 * T4: layout-a vs layout-b → pct > 0.05 (P)
 */
import { test, expect } from '@playwright/test';
import { pathToFileURL } from 'node:url';
import * as path from 'node:path';
import { discoverRoutes, grayscaleDiff64 } from './helpers';

const FX = path.join(__dirname, 'selftest-fixtures');
const start = pathToFileURL(path.join(FX, 'index.html')).toString();

test('T1 keşif + dead-link + zero-console-error', async ({ page }) => {
  const r = await discoverRoutes(page, start, 10);
  const urls = r.visited.map(v => v.url);
  expect(urls.length).toBeGreaterThanOrEqual(2);            // index + page2
  expect(urls.some(u => u.includes('page2.html'))).toBe(true);
  expect(r.deadLinks.some(d => d.url.includes('missing-page'))).toBe(true);
  for (const v of r.visited) expect(v.consoleErrors).toEqual([]);
});

test('T2 file:// kapsam — dizin DIŞI link elenir', async ({ page }) => {
  const r = await discoverRoutes(page, start, 10);
  const all = [...r.visited.map(v => v.url), ...r.deadLinks.map(d => d.url)];
  expect(all.some(u => u.includes('outside.html'))).toBe(false);
});

test('T3 aynı sayfa → diff ~0', async ({ page }) => {
  await page.goto(pathToFileURL(path.join(FX, 'layout-a.html')).toString());
  const s1 = await page.screenshot();
  const s2 = await page.screenshot();
  const d = await grayscaleDiff64(page, s1, s2);
  expect(d.pct).toBeLessThan(0.02);
});

test('T4 layout farkı → diff belirgin', async ({ page }) => {
  await page.goto(pathToFileURL(path.join(FX, 'layout-a.html')).toString());
  const sa = await page.screenshot();
  await page.goto(pathToFileURL(path.join(FX, 'layout-b.html')).toString());
  const sb = await page.screenshot();
  const d = await grayscaleDiff64(page, sa, sb);
  expect(d.pct).toBeGreaterThan(0.05);
});
