---
paths: **/*.abap
---

# ABAP stil alt kümesi — kısa işaretçi (L1b; `.abap` okununca yüklenir)

**Tam metin + gerekçe + ayıklanan noktalar:** `core/standards/11-clean-abap-ve-oo-alt-kumesi.md`
(SAP/styleguides Clean ABAP'tan seçilmiş, CC BY 3.0 — https://creativecommons.org/licenses/by/3.0/ —
kendi cümlelerimizle uyarlanmış).

**Profil:** yalnız `sap_profile: s4_private` projelerde uygulanır (std 11 `applies_to`). Profil dışında
(ör. `ecc` — 7.40 öncesi sürümde `DATA(...)`, 7.40 SP08 öncesinde `xsdbool` sözdizimi hatasıdır) std 11 ve bu kural UYGULANMAZ.

## Kapsam (MUST)
- **Yalnız YENİ yazdığın ya da bu iş kapsamında DEĞİŞTİRDİĞİN satıra uygulanır.** Mevcut kodu
  düzeltme gerekçesi DEĞİLDİR — dokunmadığın satıra stil düzeltmesi yapma, "temizlik" önerme.
- **Çelişkide mevcut standart üstündür:** KESİN YASAKLAR > paket `.rules.md` > std 02/05/06 + ADR 0012 > stil alt kümesi.
- Gate değil; bulgu `[ÖNERİ]` düzeyindedir. Test zorunluluğu eklemez/kaldırmaz (std 02 UNIT TEST + proje test politikası).

## Beş kısa kural (yeni/değişen satır)
1. Mantıksal değer `abap_bool` / `abap_true` / `abap_false`; koşuldan değer `xsdbool( )`.
2. Satır içi bildirim (`DATA(...)`) — ⚠ döngü içi sayaç/bayrak/biriktiricide YAZMA (BE-50).
3. Tek sonuç `RETURNING` — dönen tablo tipi key ifadeli, tam tipli (BE-57); biriktirilen tabloyu `EXPORTING` ile döndürme (BE-78).
4. Olumlu koşul + erken `RETURN`; uzun `ELSEIF` zinciri yerine `CASE`.
5. Yeni sınıf varsayılan `FINAL`, üyeler `PRIVATE`; desen ihtiyaç doğmadan uygulanmaz (YAGNI).

## Bu evde GEÇERLİ OLMAYAN Clean ABAP önerileri (karıştırma)
- Ad ön-ekleri (`lv_`/`lt_`/`gs_`…) **zorunludur** (std 06 §6).
- ALV aracı std 06 §3 + ADR 0012'ye göre seçilir (SALV "tercih" kuralı yok).
- BAPI/RFC'de `BAPIRET2`, RAP/EML'de `failed`/`reported` korunur ("yalnız istisna" kuralı daraltıldı).
- Test-double / constructor injection varsayılan tasarım değildir.
