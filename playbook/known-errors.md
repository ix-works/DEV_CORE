---
applies_to: [s4_private]
layer: L3
scope: project-wide
type: playbook
applies-to: backend
last-updated: 2026-05-14
status: active
---

# Bilinen Hatalar ve Çözümlü Durumlar

## 31. Bilinen Hatalar ve Çözümlü Durumlar

### 12.1 SmartFilterBar — Vkorg/Vtweg/Spart Görünmüyor

**Sebep:** CDS/SADL mekanizmasıyla oluşturulan entity type'ında property'ler SEGW'den `filterable` yapılamıyor.

**Çözüm A (Uygulandı):** MPC_EXT `DEFINE` metodunda `set_filterable( iv_filterable = abap_true )` çağrısı.

**Çözüm B (Uygulandı):** SmartFilterBar tamamen kaldırılıp manuel `sap.m` Panel + Input/Select yapıldı. SmartTable `smartFilterId` bağlantısı da kaldırıldı.

### 12.2 sap.f.DynamicSideContent — 404

**Sebep:** `sap/f` kütüphanesi SAPUI5 1.120'de yüklenmedi / 404 veriyor.

**Çözüm:** `sap.ui.layout.Splitter` (orientation="Horizontal", 70%/30%) kullanıldı.
- `xmlns:l="sap.ui.layout"` namespace eklendi
- `xmlns:f="sap.f"` ve manifest `libs`'den `sap.f` kaldırıldı

### 12.3 manifest.json Annotation URL — 400

**Sebep:** `ZSD_ORDER_SRV_VAN` annotation servisi SAP'de kayıtlı değil.

**Çözüm:** `mainAnnotation` dataSource ve `settings.annotations` array'i manifest'ten tamamen kaldırıldı.

### 12.4 i18n Dil Sorunu

**Çözüm:**
```json
"i18n": {
  "bundleUrl": "i18n/i18n.properties",
  "supportedLocales": ["", "tr"],
  "fallbackLocale": ""
}
```
`fallbackLocale: ""` boş string — varsayılan `.properties` dosyasını kullanır.

### 12.5 syntax_check.py Yanlış Hata Raporu

**Durum:** `syntax_check.py` bazen gerçekte hata olmayan durumları hata olarak raporlar.
Özellikle CDS/class interaksiyonunda ve SADL mekanizmasıyla oluşturulan entity type'larda.

**Kural:** syntax_check hata verse bile `activate_object.py` dene. Gerçek aktivasyon başarılı olabilir. SAP GUI'den kontrol et.

---


### 12.6 Klasik Dynpro/GUI-status üretimi (C1) — dialog/generate/lock hataları

Hepsi `RPY_DYNPRO_INSERT` / `RS_CUA_INTERNAL_*` ile klasik ekran/status üretiminde çıktı; **tam reçete + çözümler: [`adt-fugr-functions.md`](adt-fugr-functions.md) §6.** Özet:

| Hata | Sebep / Çözüm |
|---|---|
| `400 "Session Timed Out"` (classrun) | RPY/RS_CUA **dialog context** ister → `adt_classrun` yapamaz. RFC-enabled FM + `/sap/bc/soap/rfc`. |
| `00264 "GUI status ... durumu eksik / not generated"` | `RS_CUA_INTERNAL_WRITE` tanımı yazar ama load üretmez → sonrasında `RS_CUA_GENERATE` çağır. |
| `423 InvalidLockHandle` (FM source push) | `set_object_source` retry/ETag stateful lock'u bozar → sıkı lock→PUT→activate→unlock (`set_function_module_source`). |
| `400 "Parameter comment blocks are not allowed"` | FM imzası `*"` block ile push edildi → **satır-içi ABAP imza** yaz. |
| `mandatory parameter BIV` (RABAX) | `RS_CUA_INTERNAL_WRITE` BIV zorunlu → FETCH'ten gelen biv'i geçir. |
| GUI status Almanca | SOAP-RFC çağrısında `sap-language` yok → logon-default dil. `sap-language=TR` geç. |
| Geri/Çıkış çalışmıyor | Donör status jenerik `&F03/&F15/&F12` map'liyor → program PAI `BACK/EXIT/CANCEL` bekliyor. pfk fcode'larını re-map et. |
