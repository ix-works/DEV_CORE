import { defineConfig } from '@playwright/test';

// G1 runtime smoke-test gate (ADR 0017). Araç = SADECE playwright-cli (MCP-browser DEĞİL).
// SAP auth: fiori dev-proxy gelen Basic-auth'u SAP'ye FORWARD ediyor (kanıtlı: 8099 + basic = 200),
// bu yüzden httpCredentials çalışır → $metadata 401 duvarı aşılır → veri/fonksiyonel akış test edilir.
// Kimlik .conn_adt'den env'e (run_ui_smoke.py); config'e ASLA hardcode değil.

const BASE_URL = process.env.SMOKE_BASE_URL || 'http://localhost:8099';
const SAP_USER = process.env.SAP_USER || '';
const SAP_PASS = process.env.SAP_PASS || '';

export default defineConfig({
  testDir: '.',
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
