---
name: _indeks-ui
description: UI/freestyle UI5 derslerinin tam indeksi
metadata: 
  node_type: memory
  type: reference
---

# UI · freestyle UI5 — tohum indeksi

> UI5/OData V2 tüketimi, deploy ve tarayıcı doğrulaması. Bu dosya `MEMORY.md`'den link'lenir; dersler burada yaşar.

**6 ders.**

- ⭐ [Elle kurulan istek sap-client tasimaz](feedback_elle-kurulan-istek-sap-client-tasimaz.md) — Manifest dışı UI5 isteği (new ODataModel, ham fetch/XHR, sServiceUrl + URL) sap-client taşımaz — iki client aynı tarayıcıda açıkken HATASIZ çapraz-client okuma/yazma; ana modelin aUrlParams'ını devret
- [F4 arama yardimi tasarim asamasinda kurgulanir](feedback_f4-arama-yardimi-tasarim-asamasinda-kurgulanir.md) — Ekran alanlarının F4/arama yardımı mimarisi TS'te alan-alan kurgulanır; build sırasında sonradan eklenmez (ZSD001 F4 sagası tekrarlanmasın)
- [Playwright basic auth header not url](feedback_playwright-basic-auth-header-not-url.md) — basic-auth proxy'li UI5 local run'da Playwright auth'u setExtraHTTPHeaders ile ver; URL'ye kimlik gömme (manifest fetch kırılır)
- ⭐ [Playwright pdf page margin ve thead tekrar tuzagi](feedback_playwright-pdf-page-margin-ve-thead-tekrar-tuzagi.md) — HTML→PDF (Playwright/Chromium) dört tuzak — dokümanın kendi @page{margin:0}'ı JS page.pdf({margin})'i SESSİZCE ezer; <thead> tekrarı bu zincirde çalışmaz, headerTemplate çalışır; marginTop SABİT OLMAZ — header içerikle büyüdüğü için ölçülerek türetilir (Chromium sabit ~2,4mm daha yüksek çizer); headerTemplate ZEMİN BOYAMAZ — orada mürekkep yalniz border+metinden gelir
- ⭐ [Sayfa kapanirken senkron xhr gitmez](feedback_sayfa-kapanirken-senkron-xhr-gitmez.md) — sayfadan ayrılırken (beforeunload/pagehide/unload) SENKRON XHR Chromium'da sunucuya gitmez (navigasyonda ölçüldü) — kilit bırakma için fetch+keepalive+CSRF; bırakmadan sonra kilit bayrağını sıfırla
- ⭐ [Tarayici araci secimi playwright vs chrome eklentisi](feedback_tarayici-araci-secimi-playwright-vs-chrome-eklentisi.md) — İki tarayıcı aracı VAR — Playwright (deterministik KAPI) ve Claude in Chrome eklentisi (canlı GÖZ); hangisi ne zaman + eklentinin kurulum durumu

<!-- makine-okunur erişilebilirlik çapası (C-MEM-01): indeks bütünlüğü kapısı
     cift-koseli-parantez linki arar, markdown link saymaz. Liste yukarıdakiyle AYNI olmalı. -->
[[feedback_elle-kurulan-istek-sap-client-tasimaz]] · [[feedback_f4-arama-yardimi-tasarim-asamasinda-kurgulanir]] · [[feedback_playwright-basic-auth-header-not-url]] · [[feedback_playwright-pdf-page-margin-ve-thead-tekrar-tuzagi]] · [[feedback_sayfa-kapanirken-senkron-xhr-gitmez]] · [[feedback_tarayici-araci-secimi-playwright-vs-chrome-eklentisi]]
