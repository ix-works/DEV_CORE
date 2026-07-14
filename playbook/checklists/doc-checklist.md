---
applies_to: [s4_private]
---
# Doc-Checklist — Kullanıcı/Teknik Dökümanlar (KD / FS / TS)

> **Doc-Gate reviewer bunu kullanır** (kod bug-gate'inin doküman karşılığı, ADR 0018 deseni). KD/FS/TS **üretilince veya değişince**, lider'e "bitti" denmeden ÖNCE **bağımsız + TAZE** bir reviewer dökümanı bu listeye karşı inceler → verdict **PASS / WARNING / BLOCKER**. Self-verify (yazarın kendi kontrolü) YETMEZ — bağımsız göz şart.
>
> Her madde **HATA** (kural ihlali — zorunlu fix) / **EKSİK** (must-do karşılanmamış) / **ÖNERİ** (bağlayıcı değil) tiplenir. Kapsam = dökümanın TAM içeriği + üretilen artefaktlar (md + HTML + PDF + ekran görüntüleri + app'e bağlanan kopya).
>
> Kaynak: `standards/04-documentation-fs-ts.md` (§1.3 görsel ilkesi · §2.3 FS · §3.3 TS · §4.2-4.5 KD) · `playbook/howto-kullanici-dokumani-pdf-ekran-goruntulu.md` (üretim+§C doğrula) · ADR 0008 (grid-liste).

## §A — KULLANICI DÖKÜMANI (KD)

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| DOC-KD-01 | **Ekran görüntüleri MOCK/TEMİZ örnek veriyle** — anlamlı/tutarlı uydurma kayıt (client-model injection). Kirli/gerçek backend kaydı (test çöpü "E2E Test"/"NR otomatik test", gerçek müşteri/PII, tutarsız satır) = ihlal. Gerçek UI evet, gerçek VERİ hayır | **BLOCKER** (HATA) | std §1.3 · howto §A/§D.0 |
| DOC-KD-02 | **Gerçek UI kullanılmış, mockup değil** (KD geliştirme-sonrası); görüntüler işaretli/numaralı (ok/daire/callout), ham değil | HIGH (HATA) | std §1.3 / §4.3 |
| DOC-KD-03 | **TÜM sub-screen'ler var** (dialog/popover/value-help-F4/picker/sihirbaz) — her biri ayrı bölüm + görüntü + alan/buton fonksiyonu; view+fragment envanteri KD'ye eşlendi (atlanan yok) | BLOCKER (EKSİK) | std §4.3 |
| DOC-KD-04 | **Grid-liste varsa BÖLÜM 4-A** (tablo başlık araçları: sıralama/filtreleme/kolonlar/varyant/Excel'e aktar/yenile + filtre çubuğu) sabit/fix anlatılmış | HIGH (EKSİK) | std §4-A · ADR 0008 |
| DOC-KD-05 | **Genel bakış: amaç + ARKA PLAN SONUCU** ("Kaydet'e basınca sistemde ne oluşur") yazılı | HIGH (EKSİK) | std §4.2 B2 |
| DOC-KD-06 | **Her tipik görev: adım adım akış + ekran görüntüsü**; emir kipi (tıkla/gir/seç) | HIGH (EKSİK) | std §4.2 B5 |
| DOC-KD-07 | **Alan rehberi** (ne/format/zorunlu + NEDEN/otomatik) + **HER buton/event operasyonu** arka-plan sonucuyla | HIGH (EKSİK) | std §4.2 B6/B7 |
| DOC-KD-08 | **Hata/mesaj tablosu**: mesaj **birebir** metin + anlam + **AKSİYON** ("ne yapmalısın") | HIGH (EKSİK) | std §4.2 B9 |
| DOC-KD-09 | **Teknik terim sızmamış** (tablo/FM/BAPI/kod yok); geçen her terim sözlükte sade; SSS + destek/iletişim var | MEDIUM (EKSİK) | std §4.2 B10-12 |
| DOC-KD-10 | **İçerik canlı UI ile güncel** (bayat ekran/akış yok — değişen UI'a göre revize edilmiş); ön koşullar (yetki/ana veri/erişim) var | HIGH (HATA) | std §4.2 B3 · feedback_done-tam-kapsam-dogrula |
| DOC-KD-11 | **Üretim doğrulandı** (howto §C): PDF gerçekten oluştu + sayfa makul; TÜM görseller HTML/PDF'de görünür (broken-image 0); app'e bağlandıysa help butonu doğru dosyayı açıyor + görseller app içinde de yükleniyor | HIGH (HATA) | howto §C |
| DOC-KD-12 | **Klasik GUI in-system F1 yardımı: fihrist + link'li detay (tek-düz-sayfa DEĞİL)** — RE fihrist (program adı) + ayrı TX detay sayfaları, `<DS:TX.<ad>>` link'lerle bağlı; üretim ZSD000_CL_DOCU + program-özel runner + gateway adt_classrun (DOCU_UPDATE — ADT REST klasik doc YAZAMAZ) | HIGH (EKSİK) | **standards/08** §1/§5 |
| DOC-KD-13 | **F1 ITF format** — her sayfa ilk satır `U1` başlık (DSYST 20-char title tuzağı → başlık U1'den gelir); bold=`<ZH>...</>` (canlı-teyitli, tag-içi-tag YOK, kapanış `</>`); TDLINE ≤132; gerçek TR + UTF-8 no-BOM + TR login; markdown/HTML-entity YOK | HIGH (HATA) | **standards/08** §3/§6 |
| DOC-KD-14 | **F1 içerik kaynağı canlı (uydurma YASAK)** — tip/değer tanımları domain fixed-value'dan (adt_get), kolon/formül FS+class'tan; varsa repo markdown KD'sine paralel; classrun readback (DOKHL state=A) + ATC Prio-1=0 doğrulandı | HIGH (HATA) | **standards/08** §5/§7 |
| DOC-KD-15 | **Ham diyagram-kaynağı KD çıktısına SIZMAMIŞ** — ` ```mermaid ` (veya başka diyagram-DSL) fence build'de render EDİLMEZ → html/pdf/app-help'te `<pre><code class="language-mermaid">flowchart…` ham KOD olarak görünür (kullanıcıya çirkin/anlamsız). Diyagram = **render edilmiş PNG** olmalı (`doc_tools.preprocess_mermaid_fences` / `render_mermaid` build'e bağlı). Kontrol: KD **md + html + pdf + app-help**'te `language-mermaid` ve ham `flowchart LR` = **0**; her diyagram `<img>`/`<figure>`. Broken-image (DOC-KD-11) bunu YAKALAMAZ — mermaid kod olarak render olur, kırık görsel değil. GATE: `check_kd_no_raw_mermaid.py`. (fit_se→booking tekrarı 2026-07-02.) | HIGH (HATA) | howto §C · doc_tools.py |

## §B — FONKSİYONEL SPESİFİKASYON (FS)

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| DOC-FS-01 | **Gerçek ekran görüntüsü YOK** — ekran **mockup + yapısal tablolarla** (alan/buton/grid/etkileşim) tanımlı (tasarım-önce zihniyet, geliştirme bitmiş olsa bile) | HIGH (HATA) | std §1.3 |
| DOC-FS-02 | **Zorunlu bölümler tam** (kapak + doküman kontrolü + giriş + iş süreci + fonksiyonel gereksinim + UI/ekran + veri + entegrasyon + yetki + raporlama + hata + test + onay) | HIGH (EKSİK) | std §2.2 |
| DOC-FS-03 | **Ne/neden** odaklı (nasıl-implemente DEĞİL); iş diliyle, çözüm-tarafsız; gereksinimler izlenebilir/numaralı | MEDIUM (EKSİK) | std §2.3 |
| DOC-FS-04 | İç tutarlılık (FS↔TS↔KD no eşleşmesi; süreç adımları ↔ gereksinim ↔ ekran çelişkisiz) | MEDIUM (EKSİK) | std §1.1 |

## §C — TEKNİK SPESİFİKASYON (TS)

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| DOC-TS-01 | **Gerçek ekran görüntüsü YOK** — detaylı ekran/UI mockup + yapısal tablo (§4.5) | HIGH (HATA) | std §1.3 / §3.2 B4.5 |
| DOC-TS-02 | **Zorunlu bölümler tam** (teknik genel bakış + obje listesi + veri sözlüğü + ekran tasarımı + program/sınıf + DB erişim + enhancement + form + interface + hata + test + transport + onay) | HIGH (EKSİK) | std §3.2 |
| DOC-TS-03 | **Obje adları/alanlar canlı sistemle tutarlı** (uydurma değil; DDL/CDS/struct gerçeğiyle); naming standardına uygun. **Klasik program include'ları:** `<PKG>_I_<PRG>_<T01/C01/O01/I01/F01/S01>` — program-kökünden TÜRER; generic `_I_TOP`/`_I_F01` (kök+numaralı-suffix yok) YASAK (std 06 §1 · gate C-INC-NAME-01 · .rules.md include alt-kuralı) | HIGH (HATA) | std §3.3 · 01-naming · 06 §1 |
| DOC-TS-04 | **Clean-core/yasak farkındalığı** (std tablo yerine released CDS; ADR 0005 ihlali anlatılmıyor) | MEDIUM (ÖNERİ) | feedback_clean-core |

## Verdict
- **PASS** → bitti denebilir.
- **WARNING** → yayınla + bulguyu lider'e/rapora yansıt.
- **BLOCKER / HATA / EKSİK** → düzelt + tekrar gate. (DOC-KD-01 mock-veri ve DOC-KD-03 sub-screen = en sık BLOCKER.)

> Checklist-DIŞI iyileştirme = `[ÖNERİ]` (bağlayıcı değil). Yeni tekrar-eden doküman tuzağı → buraya DOC-XX-NN satırı ekle ([[feedback_review-bulgulari-bug-checkliste-routing]] deseni).
