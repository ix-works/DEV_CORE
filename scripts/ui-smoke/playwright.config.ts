import { defineConfig } from '@playwright/test';

// G1 runtime smoke-test gate (ADR 0017). Araç = SADECE playwright-cli (MCP-browser DEĞİL).
// SAP auth: fiori dev-proxy gelen Basic-auth'u SAP'ye FORWARD ediyor (kanıtlı: 8099 + basic = 200),
// bu yüzden httpCredentials çalışır → $metadata 401 duvarı aşılır → veri/fonksiyonel akış test edilir.
// Kimlik .conn_adt'den env'e (run_ui_smoke.py); config'e ASLA hardcode değil.

const BASE_URL = process.env.SMOKE_BASE_URL || 'http://localhost:8099';
const SAP_USER = process.env.SAP_USER || '';
const SAP_PASS = process.env.SAP_PASS || '';

// VARSAYILAN KOŞUM = YALNIZ JENERİK SMOKE (2026-08-10).
// Önceki hâlde `testMatch` yoktu → `run_ui_smoke.py --port N` (yani --spec'siz
// varsayılan kullanım) dizindeki TÜM spec'leri topluyordu (ölçüldü: 3 dosya /
// 6 test). `shipment.driver.spec.ts` UYGULAMAYA-ÖZELdir; başka bir app'in
// portunda koşunca G1 YANLIŞ-POZİTİF blok üretir.
// ⚠ Bu bulgu 2026-08-01'den beri açıktı ama ZARARSIZDI — çünkü sarmalayıcı
// (run_ui_smoke.py) proje-kökü hatası yüzünden zaten ölüydü. Aynı gün
// sarmalayıcı düzeltilince bulgu SİLAHLANDI; bu satır o yüzden eklendi.
// Ders: bir aracı diriltmek, onun uyuyan bulgularını da uyandırır.
// `--spec <dosya>` ile AÇIK çağrı bu filtreden etkilenmez (bilinçli seçimdir).
const DEFAULT_SPEC = 'ui.smoke.spec.ts';

export default defineConfig({
  testDir: '.',
  testMatch: process.env.SMOKE_SPEC ? [process.env.SMOKE_SPEC] : [DEFAULT_SPEC],
  timeout: 60_000,
  retries: 0,                       // LOCKOUT-SAFE: yanlış kimlikte retry YOK (SAP 2-deneme kilidi)
  reporter: [['list']],
  use: {
    baseURL: BASE_URL,
    headless: true,
    ignoreHTTPSErrors: true,
    httpCredentials: SAP_USER ? { username: SAP_USER, password: SAP_PASS } : undefined,
  },
});
