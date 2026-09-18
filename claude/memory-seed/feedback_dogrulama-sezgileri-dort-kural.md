---
name: feedback_dogrulama-sezgileri-dort-kural
description: "Doğrulama sezgileri — 2026-07-09'un dört ayrı hatası tek dört cümleye indirgeniyor; gate'lerin pointer'ı yerine BUNLAR hatırlanmalı"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: bd8aa28d-e506-4e59-acf0-f78058bee629
---

2026-07-09 sağlık denetiminde dört farklı yerde tökezlendi. Dördü de aynı dört sezginin eksikliğiydi. Yeni kural ezberlemek yerine bunları uygula:

1. **"Bulunamadı" ≠ sonuç.** Bir arama boş dönüyorsa, sorunun *önkoşulu* sağlandı mı diye sor. `adt_where_used count=0` (obje yok mu, tüketicisi mi yok?), `Grep` kökten 0 sonuç (yok mu, görünmüyor mu?), `entity_type_span → None`, `find core` → 0. Boş sonuç iki dünyayı ayırt etmiyorsa, o araç o soruya cevap veremez.

   ⭐ **NE ZAMAN kontrol grubu koşarsın — tetikleyici: sonuç İŞİNE GELDİĞİNDE.** (2026-09-02,
   ölçüldü.) Bir `.ccau` canlıda var mı diye soruldu; ilk okuma **404** döndü ve bu, o an
   açık duran bir çelişkinin *bir tarafına birebir uyuyordu* (*"ajan haklı, dosya SAP'ye
   gitmemiş"*). ⛔ **Yanlış cevabın en uzağa gittiği an tam olarak budur:** beklentiyi
   doğrulayan sonuç sorgulanmaz, çünkü sorgulanacak bir gerilim hissedilmez.
   Sigortası ucuzdu — **aynı çağrı, olmadığı iddia edilemeyecek objelere**: dört sınıf daha
   denendi, **beşi de 404** ⇒ hata çağrıdaydı (uç yanlıştı), objede değil.
   ⇒ Kural: *"bulunamadı"* + *"zaten böyle olmasını bekliyordum"* **birlikte** geldiğinde,
   raporlamadan önce **kontrol grubu** koştur. Tek başına *"bulunamadı"* şüphe için yeter,
   ama ikisi bir aradayken şüphe **kaybolur** — asıl tehlike odur.

2. **Kod ≠ kablolama.** Guard bir tool'u tanıyabilir ama hook o tool'da hiç tetiklenmeyebilir. Guard'ı doğrudan çağıran test yeşil verir, üretimde koruma yoktur. Kablolamayı ayrıca doğrula (matcher/registry/config), tercihen canlı A/B ile.

3. **Sayı ≠ format.** "6/6 dosya var, içerik doğru" yüklenebilirlik demek değildir. Agent dosyası `---` ile başlamıyorsa hiç yüklenmez. Doğrulama, tüketicinin gerçekten kabul ettiği biçimi sınamalı.

4. **Çökme ≠ FAIL.** `exit 1` bir kontrolün "hayır" demesi olabilir, ya da çökmesi. Windows cp1252'de Türkçe basan script `UnicodeEncodeError` verir. Negatif testte önce **bozmanın gerçekleştiğini** doğrula; `sed`/`assert` tutmadıysa test hiç koşmamıştır.

**Neden bu dosya:** gate'lenmiş bir kuralın memory'de pointer'ı gürültüdür — gate zaten zorluyor. Memory'ye kuralın kendisi değil, onu doğuran **genellenebilir sezgi** yazılır. Bkz. [[project_saglik-denetimi-2026-07-09]] ve `governance/HEALTHCHECK-PROTOKOL.md`.
