# UI Smoke-Test Gate (G1, ADR 0017)

Freestyle UI5 build'in **runtime** doğrulaması — render crash / routing crash / `$metadata` 401 (auth kopuk) / undefined hatalarını **kullanıcı testinden ÖNCE** yakalar. Statik tuzaklar G3 (`check_ui5_freestyle_traps.py`); bu runtime kısmı.

**Araç = SADECE playwright-cli** (headless, scriptli, tekrarlanabilir). MCP-browser GATE'te kullanılmaz (her run yavaş + auth'suz 401); MCP yalnız ad-hoc debug.

## Auth nasıl çözüldü
fiori dev-proxy gelen **Basic-auth'u SAP'ye forward ediyor** (kanıt: `localhost:8099 + basic = 200`). Bu yüzden playwright `httpCredentials` ile `.conn_adt` kimliğini geçirir → `$metadata` 401 duvarı aşılır → veri/fonksiyonel akış test edilir. Kimlik config'e ASLA hardcode değil; runner `.conn_adt`'den env'e koyar.

⚠️ **Lockout-safe:** runner playwright'tan ÖNCE kimliği TEK kez doğrular; 401 ise DURUR (SAP 2-yanlış-giriş kilidi). `retries: 0`.

## Kullanım
```bash
# Ön koşul (tek sefer): bu klasörde
npm install
npx playwright install chromium

# App çalışıyorken (npm run start-noflp -- --port 8099):
python scripts/ui-smoke/run_ui_smoke.py --port 8099
python scripts/ui-smoke/run_ui_smoke.py --base-url http://localhost:8097
```

## Dosyalar
- `playwright.config.ts` — httpCredentials (env'den) + baseURL + headless + retries:0
- `ui.smoke.spec.ts` — GENERIC smoke: zero gerçek console-error + `$metadata` 200 + sayfa doldu. Dev-noise allowlist (Component-preload/i18n_tr/favicon/fallback-locale). **App-spesifik akış (Create/Change kaydet) için bu spec KOPYALANIP genişletilir** (G2 §K plumbing'i KORU, içeriği bespoke).
- `run_ui_smoke.py` — `.conn_adt` → env + lockout-safe auth ön-doğrula → `npx playwright test`.

## "Done" kriteri (G4, AGENTS.md §2)
UI build "done" demeden önce bu gate PASS olmalı + G3 (`check_ui5_freestyle_traps.py`) PASS.
