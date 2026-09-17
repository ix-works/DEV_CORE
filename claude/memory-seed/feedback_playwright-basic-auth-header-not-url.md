---
name: feedback_playwright-basic-auth-header-not-url
description: "basic-auth proxy'li UI5 local run'da Playwright auth'u setExtraHTTPHeaders ile ver; URL'ye kimlik gömme (manifest fetch kırılır)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e6b9270c-63b2-41a5-8ea3-61f8051c75ab
---

basic-auth proxy'li UI5 lokal çalıştırmada (ui5.yaml proxy → canlı SAP, basic auth) Playwright'a kimliği `page.setExtraHTTPHeaders({Authorization:'Basic <b64>'})` ile ver — URL'ye GÖMME (`http://user:pass@host`).

**Why:** URL'ye kimlik gömmek `fetch('./manifest.json')`'ı kırar → tarayıcı "Request cannot be constructed from a URL that includes credentials" atar → Component manifest yüklenmez → `getRouter()` undefined → BOŞ sayfa (sessiz). UI hatası gibi görünür ama kök neden kimlik aktarım yöntemi.

**How to apply:** UI5 freestyle app'i canlı-proxy ile Playwright'ta doğrularken: server'ı `start-noflp` ile aç, Authorization header'ı `setExtraHTTPHeaders` ile geçir, `page.goto` URL'sinde kimlik kullanma. ZSD001 delivery_report 18-kolon doğrulamasında canlı yakalandı (2026-06-29). [[feedback_grid-ui-local-run-popup]] ile farklı tuzak (o lrep 401/hesap-kilidi; bu manifest-fetch credential).
