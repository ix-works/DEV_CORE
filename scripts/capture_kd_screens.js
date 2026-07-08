/**
 * KD ekran görüntüsü üreteci — ZSD011 Fittings Sipariş (mock UI, panel-bazlı kırpma).
 *
 * Reçete: playbook/howto-kullanici-dokumani-pdf-ekran-goruntulu.md §A.
 *   - Mock sunucu çalışır olmalı: cd ui/fittings_order_rap && npm run start-mock  (port log'dan)
 *   - Türkçe locale ŞART (?sap-ui-language=tr)
 *   - Bakiye/Fiyat ve bazı F4'ler function-import/ayrı-servis → mock'ta boş → eval ile state enjekte.
 *   - Panel-bazlı: her ekran bölmesi (Başlık, Bakiye, Kalem tablosu, Kalem Detay ⓘ, Özet, Notlar,
 *     Depo/Teslimat dialog) AYRI kırpılır → kullanıcı her bölümü tek tek görür.
 *
 * Çalıştır:  node scripts/capture_kd_screens.js [http://localhost:PORT]
 * Çıktı   :  ERP/SD/ZSD011_CLC/docs/screenshots/kd-*.png
 */
const path = require("path");
const PW = "C:/Users/DELL/AppData/Roaming/npm/node_modules/@playwright/cli/node_modules/playwright-core";
const { chromium } = require(PW);

const URL = (process.argv[2] || "http://localhost:8092").replace(/\/$/, "");
const OUT = path.resolve(__dirname, "..", "ERP", "SD", "ZSD011_CLC", "docs", "screenshots");

// ── Zengin örnek state (TEMİZ örnek veri; KVKK/gerçek-veri yok) ──────────────
const STATE = {
  header: {
    salesOrderType: "ZC01", salesOrderTypeName: "Fittings Siparişi",
    salesOrganization: "1500", distributionChannel: "30", division: "10",
    soldToParty: "0000300001", soldToPartyName: "ÖRNEK MÜŞTERİ A.Ş.",
    shipToParty: "0000300001", shipToPartyName: "ÖRNEK MÜŞTERİ A.Ş.",
    deliveryAddress: "0000300042", deliveryAddressName: "ÖRNEK MÜŞTERİ A.Ş. — Merkez Depo",
    deliveryAddressText: "Atatürk OSB Mah. 10019 Sok. No:5 / Çiğli / İZMİR",
    depot: "0000300077", depotName: "ÖRNEK LOJİSTİK AMBAR (İzmir)",
    currency: "TRY", purchaseOrderByCustomer: "PO-2026-100",
    priceCode: "2026-03-21", priceCodeDescription: "ÇEK 60 GÜN VADE", discountCode: "Z47",
    pricingDate: "20260611",
    orderNote1: "Sevkiyat öncesi müşteriyi arayın.", orderNote2: "Paletli teslim.",
    deliveryNote: "İrsaliyeye sipariş referansı yazılsın."
  },
  items: [
    { itemNumber: "10", material: "FT-DIRSEK-90", materialName: "Fittings Dirsek 90°", kdmat: "CM-1001",
      quantity: 10, unit: "ADT", pakFactor: 5, netAmount: 3259.5, taxAmount: 651.9, totalAmount: 3911.4,
      currency: "TRY", mengeSe: 0, deliveryQty: 0, availStock: 240, netWeightPerUnit: 2.4, gewei: "KG",
      lgort: "1001", lgortText: "Mamul Ambarı", qtyError: false },
    { itemNumber: "20", material: "FT-TE-110", materialName: "Fittings Te 110 mm", kdmat: "CM-1002",
      quantity: 15, unit: "ADT", pakFactor: 5, netAmount: 6187.5, taxAmount: 1237.5, totalAmount: 7425.0,
      currency: "TRY", mengeSe: 5, deliveryQty: 0, availStock: 90, netWeightPerUnit: 3.1, gewei: "KG",
      lgort: "1001", lgortText: "Mamul Ambarı", qtyError: false },
    { itemNumber: "30", material: "FT-REDUKSIYON-75", materialName: "Fittings Redüksiyon 110/75", kdmat: "CM-1003",
      quantity: 20, unit: "ADT", pakFactor: 10, netAmount: 4760.0, taxAmount: 952.0, totalAmount: 5712.0,
      currency: "TRY", mengeSe: 0, deliveryQty: 10, availStock: 12, netWeightPerUnit: 1.8, gewei: "KG",
      lgort: "1002", lgortText: "Sevk Alanı", qtyError: false }
  ],
  balance: [
    { FiyatKodu: "2026-03-21", Aciklama: "ÇEK 60 GÜN VADE", IndirimKodu: "Z47", TutarBakiye: 250000.00, TutarBakiyeSe: 18500.00, Waers: "TRY" },
    { FiyatKodu: "2026-02-10", Aciklama: "NAKİT PEŞİN", IndirimKodu: "Z10", TutarBakiye: 120000.00, TutarBakiyeSe: 0.00, Waers: "TRY" },
    { FiyatKodu: "2026-01-05", Aciklama: "BANKA HAVALESİ 30 GÜN", IndirimKodu: "Z30", TutarBakiye: 75000.00, TutarBakiyeSe: 5000.00, Waers: "TRY" }
  ],
  summary: {
    totalNetAmount: 14207.0, totalTaxAmount: 2841.4, totalGrossAmount: 17048.4,
    selectedBalance: 250000.0, balanceStatus: "Success",
    // tutarlılık: totalPackages = Σ(qty×pakFactor)=50+75+200; totalWeight = Σ(qty×netWeightPerUnit)
    totalAdt: 45, totalPackages: 325, totalWeight: 106.5, weightUnit: "KG"
  },
  state: { priceCalculated: true, hasDelivery: false, isChange: false }
};

const shots = [];
async function shot(page, selector, name, opts) {
  try {
    const el = page.locator(selector).first();
    await el.waitFor({ state: "visible", timeout: 8000 });
    await el.screenshot(Object.assign({ path: path.join(OUT, name) }, opts || {}));
    shots.push("OK   " + name);
  } catch (e) {
    shots.push("FAIL " + name + " :: " + String(e).split("\n")[0]);
  }
}

(async () => {
  const browser = await chromium.launch({ channel: "msedge", headless: true, args: ["--no-sandbox"] });
  const ctx = await browser.newContext({ viewport: { width: 1680, height: 1050 }, ignoreHTTPSErrors: true, locale: "tr-TR", deviceScaleFactor: 2 });
  const page = await ctx.newPage();

  await page.goto(URL + "/index.html?sap-ui-language=tr", { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForFunction(() => window.sap && sap.ui && sap.ui.getCore && sap.ui.getCore().isInitialized(), null, { timeout: 60000 });
  // Liste render olana kadar bekle (mock veri)
  await page.waitForFunction(() => /0001000101/.test(document.body.innerText), null, { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(1500);

  // ── LİSTE ekranı (tam görünüm) ──
  await shot(page, '[id$="listPage"]', "kd-liste-tam.png");
  // Filtreler panelini aç + çek (id-ending selector re-render'a dayanıklı)
  await page.evaluate(() => {
    const fp = sap.ui.core.Element.registry.filter(e => e.getId && /--filterPanel$/.test(e.getId()))[0];
    if (fp && fp.setExpanded) fp.setExpanded(true);
  });
  await page.waitForTimeout(1200);
  await shot(page, '[id$="filterPanel"]', "kd-liste-filtre.png");

  // ── "Yeni Sipariş" → Create ekranı (router getRouter() falsy → UI tıklama) ──
  await page.locator('button:has-text("Yeni Sipariş")').first().click();
  await page.waitForFunction(() => sap.ui.core.Element.registry.filter(e => e.isA && e.isA("sap.ui.core.mvc.View") && /CreateOrder/.test(e.getControllerName ? e.getControllerName() : "")).length > 0, null, { timeout: 30000 });
  await page.waitForTimeout(2000);

  // orderModel state enjekte + panelleri data-kd ile etiketle
  await page.evaluate((st) => {
    const views = sap.ui.core.Element.registry.filter(e => e.isA && e.isA("sap.ui.core.mvc.View") && /CreateOrder/.test(e.getControllerName ? e.getControllerName() : ""));
    const view = views[0];
    if (!view) return "no-view";
    const m = view.getModel("orderModel");
    m.setData(st);
    m.refresh(true);
    // Notlar panelini aç (id'siz; re-render olacağı için etiketleme AYRI adımda)
    const notes = view.findAggregatedObjects(true, c => c.isA && c.isA("sap.m.Panel") && /Not/.test((c.getHeaderText && c.getHeaderText()) || ""))[0];
    if (notes && notes.setExpanded) notes.setExpanded(true);
    return "ok";
  }, STATE);
  await page.waitForTimeout(2000);

  // id'siz panelleri (Özet/Bakiye/Notlar) stabil-DOM'da data-kd ile etiketle
  await page.evaluate(() => {
    const views = sap.ui.core.Element.registry.filter(e => e.isA && e.isA("sap.ui.core.mvc.View") && /CreateOrder/.test(e.getControllerName ? e.getControllerName() : ""));
    const panels = views[0].findAggregatedObjects(true, c => c.isA && c.isA("sap.m.Panel"));
    panels.forEach(p => {
      const h = (p.getHeaderText && p.getHeaderText()) || "";
      const d = p.getDomRef && p.getDomRef();
      if (!d) return;
      if (h.indexOf("Özet") >= 0) d.setAttribute("data-kd", "summary");
      else if (h.indexOf("Bakiye") >= 0) d.setAttribute("data-kd", "balance");
      else if (h.indexOf("Not") >= 0) d.setAttribute("data-kd", "notes");
    });
  });
  await page.waitForTimeout(500);

  // ── Panel-bazlı kırpmalar (id-ending selector re-render'a dayanıklı) ──
  await shot(page, '[id$="createPage"]', "kd-yarat-tam.png");
  await shot(page, '[id$="headerPanel"]', "kd-panel-baslik.png");
  await shot(page, '[id$="itemPanel"]', "kd-panel-kalemler.png");
  await shot(page, '[data-kd="summary"]', "kd-panel-ozet.png");
  await shot(page, '[data-kd="balance"]', "kd-panel-bakiye.png");
  await shot(page, '[data-kd="notes"]', "kd-panel-notlar.png");

  // ── Kalem Detay (ⓘ) popover — 1. satırın bilgi düğmesine bas ──
  try {
    await page.evaluate(() => {
      const views = sap.ui.core.Element.registry.filter(e => e.isA && e.isA("sap.ui.core.mvc.View") && /CreateOrder/.test(e.getControllerName ? e.getControllerName() : ""));
      const tbl = views[0].byId("itemTable");
      const row = tbl.getItems()[0];
      const cells = row.getCells();
      const btn = cells[cells.length - 1];
      btn.firePress();
    });
    await page.waitForTimeout(1200);
    await shot(page, ".sapMPopover", "kd-popover-kalemdetay.png");
    await page.evaluate(() => { sap.ui.core.Element.registry.filter(e => e.isA && e.isA("sap.m.Popover") && e.isOpen && e.isOpen()).forEach(p => p.close()); });
    await page.waitForTimeout(600);
  } catch (e) { shots.push("FAIL kd-popover-kalemdetay :: " + String(e).split("\n")[0]); }

  // ── Yeni Loj. Depo dialog — controller.onNewDepot() + örnek değerler ──
  try {
    await page.evaluate(() => {
      const views = sap.ui.core.Element.registry.filter(e => e.isA && e.isA("sap.ui.core.mvc.View") && /CreateOrder/.test(e.getControllerName ? e.getControllerName() : ""));
      views[0].getController().onNewDepot();
    });
    await page.waitForTimeout(1200);
    await page.evaluate(() => {
      const dlg = sap.ui.core.Element.registry.filter(e => e.isA && e.isA("sap.m.Dialog") && e.isOpen && e.isOpen())[0];
      if (dlg) {
        const nm = dlg.getModel("newAddr");
        if (nm) nm.setData({ companyName: "ÖRNEK LOJİSTİK AMBAR", street: "Atatürk OSB Mah. 10019 Sok.", strSuppl1: "Egemenlik", district: "Çiğli", city: "İZMİR", country: "TR", region: "35", postalCode: "35620", transportZone: "TR0035", transportZoneName: "Ege Bölgesi" });
      }
    });
    await page.waitForTimeout(800);
    await shot(page, ".sapMDialog", "kd-dialog-depot.png");
    await page.evaluate(() => { sap.ui.core.Element.registry.filter(e => e.isA && e.isA("sap.m.Dialog") && e.isOpen && e.isOpen()).forEach(d => d.close()); });
    await page.waitForTimeout(600);
  } catch (e) { shots.push("FAIL kd-dialog-depot :: " + String(e).split("\n")[0]); }

  console.log("\n=== SHOT SONUÇLARI ===");
  shots.forEach(s => console.log(" ", s));
  console.log("Toplam:", shots.length, "| OK:", shots.filter(s => s.startsWith("OK")).length);

  await browser.close();
})().catch(e => { console.error("FATAL:", e); process.exit(1); });
