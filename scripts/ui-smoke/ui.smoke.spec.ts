import { test, expect } from '@playwright/test';

// G1 GENERIC smoke (ADR 0017): herhangi bir freestyle UI5+V2 app'i için. SMOKE_BASE_URL ile app seç.
// Yakaladıkları: render crash (core:Title VBox-child gibi), routing target crash, undefined hatası,
// $metadata 401 (auth kopuk). App-spesifik akış (Create/Change kaydet) için bu spec KOPYALANIP genişletilir.

// Dev-noise allowlist — build-edilmemiş dev modunun NORMAL 404'leri; gerçek hata DEĞİL.
const IGNORE = [
  'Component-preload.js',
  'i18n_tr.properties',
  'favicon.ico',
  'sap-ui-core.js:269',        // ui5 cdn opsiyonel resource
  'unload is not allowed',     // permissions-policy uyarısı (zararsız)
  'Failed to load resource: the server responded with a status of 404',
  'is not contained in the list of supported locales',  // i18n_tr fallback (dev-noise; UI5 error-level loglar)
  'fallback locale',
];

function isReal(msg: string): boolean {
  return !IGNORE.some((s) => msg.includes(s));
}

test('render smoke — zero gerçek console error + $metadata 200 (auth) + sayfa doldu', async ({ page }) => {
  const errors: string[] = [];
  let metaStatus = -1;

  page.on('console', (m) => {
    if (m.type() === 'error' && isReal(m.text())) errors.push(m.text());
  });
  page.on('pageerror', (e) => {
    if (isReal(String(e))) errors.push('pageerror: ' + String(e));
  });
  page.on('response', (r) => {
    if (r.url().includes('$metadata')) metaStatus = r.status();
  });

  await page.goto('/index.html?sap-ui-xx-viewCache=false', { waitUntil: 'load' });
  await page.waitForTimeout(5000); // UI5 boot + ilk view render + $metadata

  // Auth çalıştı mı: $metadata 200 olmalı (401 = httpCredentials kopuk)
  expect(metaStatus, `$metadata status=${metaStatus} (200 bekleniyor; 401 = auth kopuk, -1 = istek hiç gitmedi)`).toBe(200);

  // Sayfa gerçekten render oldu mu (boş/crash değil)
  const bodyText = await page.locator('body').innerText().catch(() => '');
  expect(bodyText.trim().length, 'sayfa boş — render crash olabilir').toBeGreaterThan(0);

  if (errors.length) {
    console.log('\nGERÇEK CONSOLE HATALARI:\n' + errors.map((e) => '  ✘ ' + e).join('\n') + '\n');
  }
  expect(errors, 'gerçek console error (aggregation/routing/undefined) bulundu').toEqual([]);
});
