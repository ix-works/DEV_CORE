---
name: feedback_alan-anlamini-ddic-etiketinden-dogrula-tvak-fkara-fkarv
description: "Uyarlama tablosu alanlarının anlamı VARSAYILMAZ, DDIC/veri-elemanı etiketinden okunur — TVAK FKARA=siparişe bağlı, FKARV=teslimata bağlı fatura tipi; RESEARCH-02 ters okudu → FS'te fatura tipi F2 (yanlış) yerine ZM12"
metadata:
  type: feedback
---

**Vaka (2026-08-17, ZSD001):** RESEARCH-02 §2 `TVAK ZC12`'yi "FKARA=F2 teslimat-ilişkili, FKARV=ZM12 sipariş-ilişkili" diye yazdı — TERS. DDIC: **FKARA = Auftragsbezogene Fakturaart (siparişe bağlı)**, **FKARV = Versand/lieferbezogene Fakturaart (teslimata bağlı)**. Teslimat bazlı faturalama yapan JOB'un fatura tipi ZM12 "YD.Konsinye Satış Fatura" — FS üç sürüm boyunca "F2" taşıdı; ECC örneği (1031574: ZYKE fatura) ile çapraz okunurken yakalandı.

**Why:** Alan adı kısaltmaları (A/V) sezgisel değil; araştırma ajanı anlamı bağlamdan tahmin etti, kimse etiketi okumadı. Yanlış fatura tipi TS/build'de fiyatlandırma/hesap tayini/çıktı belirlemede yanlış uyarlamaya götürürdü.

**How to apply:** Uyarlama/kontrol tablosu alanı raporlanırken (TVAK/TVLK/TVFK/T184/TVCPA…) **DTEL etiketini** (adt_get dtel ya da DDIC label) rapora yaz; "hangisi teslimat-bağlı" gibi ikili alanlarda ikisini de etiketle. Doğrulama: aynı türden bir gerçek belge zinciriyle (ECC/S4 örnek sipariş→fatura FKART) çapraz kontrol. Doc-gate: FS'te fatura/teslimat türü iddiası varsa kaynağını iste.

İlgili: [[project_zsd001-<MUSTERI-D>-konsinye]], [[feedback_dogrulama-sezgileri-dort-kural]], [[feedback_legacy-field-adlari-sistem-bagimli]]
