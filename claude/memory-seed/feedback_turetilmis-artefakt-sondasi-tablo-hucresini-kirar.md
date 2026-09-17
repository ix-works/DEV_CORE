---
name: feedback_turetilmis-artefakt-sondasi-tablo-hucresini-kirar
description: "md'den kopyalanan ÇOK HÜCRELİ sonda html/pdf'te ASLA eşleşmez — içerik girmiş olsa bile 'girmemiş' okunur; hücre-düzeyi kısa sonda kullan"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 8f4adc5a-1688-42ff-8ec6-326eec08276e
---

Türetilmiş artefaktı (`.html` / `.pdf`) içerik sondasıyla doğrularken, `.md`'den **kopyala-yapıştır**
bir tablo satırı sonda olarak kullanılamaz. İçerik artefakta girmiş olsa bile sonda **0** döner ve
"türetilmiş artefakt bayat" diye okunur — yanlış bulgu üretir.

**Neden (mekanizma, ölçüldü):**
- `pdftotext -layout` tablo hücrelerini **sütun genişliğinde kırar**. `Değişecek (mevcut, KR-035)`
  → `Değişecek` / `(mevcut, KR-` / `035)` üç ayrı satıra düşer ve **aralarına diğer sütunların
  metni girer**. Düz `pdftotext` de çözmez (o da sütun-major gruplar üretir).
- HTML'de tablo `|` karakteri **hiç yoktur** (`<td>`/`<tr>`), ayrıca `**…**` ve `` `…` ``
  markdown vurguları araya `<strong>`/`<code>` etiketi sokar.

**Vaka (2026-09-09, ZSD001 FS/TS konsinye kapsama turu):** ilk sonda turunda 4 sonda "FAIL" verdi;
dördünün de içeriği PDF'te **mevcuttu**. Aynı turda HTML tarafında `MAX(0, …) tabanı zorunludur`
ham metinde 0 çıktı, etiketler sıyrılınca 1.

**Nasıl uygula:**
- **Hücre düzeyi kısa sonda** seç — tek hücreden çıkmayan, 2-4 kelimelik ayırt edici parça
  (`ZE04,ZE07` · `Customer = havuz_muhatabi` · `PARVW='SB'].KUNNR`).
- Ya da **sıkıştırılmış karşılaştırma**: boşluk/`|`/backtick/`*` atıp normalize et. ⚠ Karakter
  sıyırmayı abartma — em-dash, kesme işareti, parantez korunmalı, yoksa "birebir" iddiası çürür.
- HTML için `<tag>` sıyır + `unescape`; PDF için PyMuPDF (`pdftotext`in UTF-8 çıktısı bu projede
  bozuk bayt verdi).
- Sonda **0** dönünce hemen "girmemiş" deme — önce **sondanın kendisini** sına: aynı içeriği
  daha kısa bir parçayla ara.

Bu, [[feedback_teslim-paketi-artefakttan-ayri-yasar]]'ın doğrulama ayağı: orada ölçülen nesnenin
kimliği kayıyordu, burada **ölçüm aracının artefaktı deforme etmesi** yanlış negatif üretiyor.
Aynı aile: [[feedback_olcumu-artefaktin-kendi-baglaminda-kos]] ·
[[feedback_exit0-degil-cikti-kaniti]] · [[feedback_deploy-ui-statik-varlik-korlugu]].
