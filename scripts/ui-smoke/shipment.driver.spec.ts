import { test, expect } from '@playwright/test';

// Shipment şöför GEÇERSİZLİK doğrulaması: elle girilen kimlik tanımlı DEĞİL + yarat-prompt IPTAL edilirse
// → (a) Input valueState "Error" + DriverInvalid=true (değer kalır), (b) create/save BLOCKED (save-guard).
// Ayrıca NewBooking diyaloğu açılırken ColumnLayout/HBox render hatası olmadığını teyit eder.
// (Şöför alanı dış-dizayn "Link" biçiminde: Input + ad-Link; info/add ikon-buton yok — controller mantığı aynı.)

const IGNORE = [
  'Component-preload.js', 'i18n_tr.properties', 'favicon.ico', 'sap-ui-core.js:269',
  'unload is not allowed', 'Failed to load resource: the server responded with a status of 404',
  'is not contained in the list of supported locales', 'fallback locale',
];
const isReal = (m: string) => !IGNORE.some((s) => m.includes(s));

function grabCtrl() {
  const Element: any = (window as any).sap.ui.require('sap/ui/core/Element');
  let ctrl: any = null;
  if (Element && Element.registry) {
    Element.registry.forEach((e: any) => {
      if (!ctrl && e.isA && e.isA('sap.ui.core.mvc.XMLView')) {
        const c = e.getController && e.getController();
        if (c && /\.Main$/.test(c.getMetadata().getName())) ctrl = c;
      }
    });
  }
  (window as any).__ctrl = ctrl;
  return !!ctrl;
}

test('shipment invalid-driver — Input Error state + create BLOCKED + render temiz', async ({ page }) => {
  const errors: string[] = [];
  page.on('console', (m) => { if (m.type() === 'error' && isReal(m.text())) errors.push(m.text()); });
  page.on('pageerror', (e) => { if (isReal(String(e))) errors.push('pageerror: ' + String(e)); });

  await page.goto('/index.html?sap-ui-xx-viewCache=false', { waitUntil: 'load' });
  await page.waitForTimeout(6000);

  const ok = await page.evaluate(grabCtrl);
  expect(ok, 'Main controller bulunamadi').toBeTruthy();

  // NewBooking ac (render-crash olursa burada patlar)
  await page.evaluate(() => { (window as any).__ctrl.onNewBooking(); });
  await page.waitForTimeout(1500);
  const dlgVisible = await page.evaluate(() => {
    const d = document.querySelector('[id$="newBookingDialog"]') as HTMLElement;
    const inp = document.querySelector('[id$="nbDriver"]') as HTMLElement;
    return { dlg: !!d && d.getBoundingClientRect().width > 0, inp: !!inp && inp.getBoundingClientRect().width > 0 };
  });
  expect(dlgVisible.dlg, 'NewBooking diyalog gorunmuyor').toBeTruthy();
  expect(dlgVisible.inp, 'nbDriver input gorunmuyor').toBeTruthy();

  // gecersiz DriverId enjekte + change tetikle; bkg create'i sar (cagrildi mi izle)
  await page.evaluate(() => {
    const c = (window as any).__ctrl;
    const bm = c._bkgModel();
    if (!bm.__wrapped) {
      const orig = bm.create.bind(bm);
      bm.create = function () { (window as any).__createCalled = true; return orig.apply(bm, arguments); };
      bm.__wrapped = true;
    }
    const inp = c.byId('nbDriver');
    c._nb.setProperty('/DriverId', '99999999999');
    c.onDriverIdChange({ getSource: () => inp, getParameter: (k: string) => (k === 'value' ? '99999999999' : '') });
  });

  // create-prompt (MessageBox) IPTAL — sadece "tanımlı değil" iceren dialog (NewBooking degil)
  const mbox = page.locator('.sapMDialog', { hasText: 'tanımlı değil' });
  await mbox.getByRole('button', { name: /İptal|Iptal|Cancel|Hayır|Hayir|No/ }).click({ timeout: 20000 });
  await page.waitForTimeout(800);

  // (a) Input valueState Error + DriverInvalid true + deger KALIR
  const st = await page.evaluate(() => {
    const c = (window as any).__ctrl;
    return { vs: c.byId('nbDriver').getValueState(), invalid: c._nb.getProperty('/DriverInvalid'), did: c._nb.getProperty('/DriverId') };
  });
  console.log('IPTAL sonrasi:', JSON.stringify(st));
  expect(st.vs, 'nbDriver valueState Error degil').toBe('Error');
  expect(st.invalid, 'DriverInvalid true degil').toBe(true);
  expect(st.did, 'DriverId temizlenmemeli (kalmali)').toBe('99999999999');

  // (b) Confirm -> create BLOCKED
  await page.evaluate(() => { (window as any).__createCalled = false; (window as any).__ctrl.onNewBookingConfirm(); });
  await page.waitForTimeout(1000);
  const createCalled = await page.evaluate(() => (window as any).__createCalled === true);
  console.log('onNewBookingConfirm sonrasi createCalled:', createCalled);
  expect(createCalled, 'GECERSIZ sofor ile create YAPILDI (save-guard calismadi)').toBe(false);

  // render temiz (ColumnLayout/HBox hatasi yok)
  const relevant = errors.filter((e) => /HBox|ColumnLayout|Form content|is not a valid/.test(e));
  console.log('ColumnLayout/HBox iliskili hatalar:', JSON.stringify(relevant));
  expect(relevant, 'ColumnLayout/HBox render hatasi').toEqual([]);
});
