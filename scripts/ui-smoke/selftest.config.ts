/** selftest.config.ts — helpers self-test'i için bağımsız config (SAP/auth GEREKMEZ;
 *  ana playwright.config.ts'e dokunmaz — o G1 gate'inin SAP'li config'i). */
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testMatch: /helpers\.selftest\.spec\.ts/,
  timeout: 30_000,
  use: { headless: true },
  reporter: [['list']],
});
