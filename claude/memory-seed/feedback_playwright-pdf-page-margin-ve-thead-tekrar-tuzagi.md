---
name: feedback_playwright-pdf-page-margin-ve-thead-tekrar-tuzagi
description: "HTML→PDF (Playwright/Chromium) dört tuzak — dokümanın kendi @page{margin:0}'ı JS page.pdf({margin})'i SESSİZCE ezer; <thead> tekrarı bu zincirde çalışmaz, headerTemplate çalışır; marginTop SABİT OLMAZ — header içerikle büyüdüğü için ölçülerek türetilir (Chromium sabit ~2,4mm daha yüksek çizer); headerTemplate ZEMİN BOYAMAZ — orada mürekkep yalniz border+metinden gelir"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 78c7bae5-81aa-4c75-a44f-1fc2d4679222
---

`html_to_pdf.js` / `render_pdf.js` gibi Playwright(Chromium) `page.pdf()` zincirinde **iki tuzak**:

1. **`@page { margin: 0 }` JS `margin` seçeneğini SESSİZCE ezer.** Dokümanın kendi CSS'inde
   `@page{margin:0}` varken `page.pdf({margin:{top:'32mm'}})` **hiçbir etki yapmaz** —
   hata da vermez. Belirti: başlık ile gövde üst üste biner ve margin değerini büyütmek
   **hiçbir şeyi değiştirmez**. Çözüm: `@page` yalnız `size: A4` yazsın, `margin`
   **JS tarafında** verilsin.
2. **`<thead>` tekrar tekniği bu zincirde ÇALIŞMIYOR.** Sayfa 2'de başlık tekrarlatmak için
   klasik "gövdeyi bir tablonun içine al, başlığı `<thead>`'e koy" deseni **iki farklı DOM
   yapısıyla denendi** (tek büyük `<td>` · kalem başına `<tr>`), ikisi de tekrarlamadı.
   Çalışan yol: Playwright'ın natif `displayHeaderFooter` + `headerTemplate` /
   `footerTemplate` (Chromium DevTools `Page.printToPDF`'in kendi mekanizması, DOM/CSS
   fragmantasyonundan bağımsız). Sayfa numarası da oradan (`pageNumber`/`totalPages`).
3. **`marginTop`/`marginBottom` SABİT OLMAZ — ÖLÇÜLEREK türetilir.** `headerTemplate` içeriğe
   göre **büyür** (uzun bir uyarı bandı, uzun müşteri adı, 2 satıra saran metin). Elle ayarlanmış
   bir mm değeri **bugün**kü içeriğe uysa bile bir sonraki metin değişikliğinde gövdenin ilk satırı
   başlığın **altında kalır** — ve bu **yalnız o sayfada** olur (ör. sayfa 1 temiz, sayfa 2 kırpık).
   Çözüm: fragmanı PDF'ten **ÖNCE** A4 genişliğinde (210mm — header/footer tam sayfa genişliğinde
   çizilir, sol/sağ content margin'inden bağımsız) geçici bir sayfada render edip **gerçek yükseklik**
   ölç → `marginTop = ölçülen + güvenlik payı`.
   ⚠ **Ölçümü `scrollHeight` ile YAPMA** — içerik viewport'tan kısaysa `scrollHeight` viewport
   yüksekliğine **eşitlenir** ve değeri yanlış büyük gösterir (canlı: viewport=100px verilince ~22px'lik
   footer *"100px"* ölçüldü). Doğrusu kök elemanın `getBoundingClientRect().height`'i.
   ⭐ **ÖLÇÜLDÜ — Chromium'un header motoru fragmanı sabit ~2,4mm DAHA YÜKSEK çizer**
   (ölçülen⇒gerçek: 51,8⇒54,2 · 55,8⇒58,2 · 115,8⇒118,2 — üçünde de **+2,4**, yani **sabit,
   orantılı DEĞİL). Ayrı probe: header bağlamında **mm birimi 1:1**'dir (`top:50mm`→55,28mm ·
   `top:100mm`→105,29mm; ikisinde de aynı 5,28mm sabit üst iç boşluk) ⇒ model doğru, yalnız
   Chromium sabit bir iç boşluk ekliyor. Güvenlik payı bu 2,4mm'yi **karşılamalı** (4mm geriye
   yalnız 1,6mm bırakır — incedir).

4. **`headerTemplate`/`footerTemplate` ZEMİN BOYAMAZ — orada mürekkep üreten tek şey
   KENARLIK ve METİNDİR.** `printBackground:true` verilse bile header/footer bağlamında
   `background-color` **hiç boyanmıyor**. Belirti **sinsi**: ters kontrast bir öğe (siyah zemin +
   beyaz yazı) beyaz kâğıtta **görünmez** olur — hata yok, uyarı yok, sayfada **boşluk** var.
   ⭐ **ÖLÇÜLDÜ** (aynı zincirde 6 teknik, `printBackground:true`):
   `border` ✅ · metin ✅ · `background-color` ⛔ · `<img>` **data-URI** ⛔ · satır-içi `<svg>` ⛔ ·
   `box-shadow: inset` ⛔. Aynı CSS gövdede %42 koyu mürekkep verirken header'da **%0** ölçüldü.
   ⇒ Her sayfada tekrarlaması gereken bir **uyarı bandı/damga** tasarlarken ayrımı **dolguya**
   değil **çerçeve kalınlığı + yazı ağırlığına** dayandır. ⚠ "Gövdeye taşı" çözüm değildir —
   gövdedeki öğe yalnız 1. sayfada görünür.
   ⛔ **Metin çıkarma bu kusuru GÖREMEZ** — `get_text()` bandın yazısını döndürür, oysa kâğıtta
   mürekkep yoktur. Kanıt **piksel** olmalı: `get_pixmap(dpi=300)` + koyu-piksel oranı.

**Why:** İkisi de **sessiz** kırıklıktır — çıktı üretilir, hata basılmaz, yalnız yanlış görünür.
Bu yüzden "PDF üretildi" mesajı doğruluk kanıtı değildir; sayfa **içeriği** görülmelidir.
Vaka: ZSD001 teslimat toplama listesi mock'u (2026-09-08), sayfa-2 başlık tekrarı gereksinimi.

✅ **KANIT DURUMU (2026-09-08 güncellendi):** 3. madde **lider tarafından bağımsız ölçüldü**
(PyMuPDF ile PDF blok koordinatları + üç farklı header yüksekliği + ayrı bir birim-ölçekleme probe'u).
1. ve 2. maddeler hâlâ **alt ajanın ölçümüdür** — lider bağımsız yeniden üretmedi; aynı sınıf bir
belirtiyle karşılaşınca önce onları dene ama *"kanıtlandı"* diye aktarma — ilk doğrulayan bu satırı
güncellesin.
⚠ **Kendi ölçümünde tuzak:** PDF'te *"header nerede bitiyor"* diye bakarken metin bloklarını
sabit bir y-eşiğiyle süzersen (ör. `y<400pt`) uzun başlıklı varyantta **gövde metnini header sanarsın**
— bu beni bir kez *"sapma orantılı"* diye yanlış hükme götürdü. Blokları **sırala ve gözle ayır**.

**How to apply:** A4 baskı çıktısı (fiş/rapor/KD) üretirken: `@page`'e margin yazma · başlık/altbilgi
tekrarı gerekiyorsa doğrudan `headerTemplate` kur, `<thead>` ile vakit kaybetme · üretilen PDF'i
**sayfa sayısı + sayfa içeriği** olarak ölç.

prior-art: bulundu — [[core/playbook/howto-kullanici-dokumani-pdf-ekran-goruntulu.md]] aynı iki
mekanizmayı (A4 `@page` + `page.pdf({margin})`) yan yana kullanıyor ama **tuzağı yazmıyor**;
ilk fırsatta oraya da not düşülmeli (T1). İlgili: [[feedback_kapi-zinciri-derlemeyi-gormez]] ·
[[feedback_exit0-degil-cikti-kaniti]] · [[feedback_ajan-bulgusu-dogru-mekanizmasi-yanlis]].
