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
| `does not implement if_oo_adt_classrun~main` (HTTP **200** gövdesinde) | Mesaj **DOĞRU**, araç bozuk değil: (1) sınıf **aktive edilmemiş** → aktif sürüm boş kabuk (classrun aktif sürümü koşar) · (2) çağıran süreç **bayat stateful oturum** tutuyor (obje başka süreçte aktive edildi). → aktive et + **`adt_inactive_objects`** doğrula · oturum RESET. ⛔ **taze class adıyla yeniden yaratma** (yanlış reçete, geri alındı 2026-07-31). [`adt-classes.md`](adt-classes.md) §24.9 |
| `00264 "GUI status ... durumu eksik / not generated"` | `RS_CUA_INTERNAL_WRITE` tanımı yazar ama load üretmez → sonrasında `RS_CUA_GENERATE` çağır. |
| `423 InvalidLockHandle` (FM source push) | `set_object_source` retry/ETag stateful lock'u bozar → sıkı lock→PUT→activate→unlock (`set_function_module_source`). |
| `400 "Parameter comment blocks are not allowed"` | FM imzası `*"` block ile push edildi → **satır-içi ABAP imza** yaz. |
| `mandatory parameter BIV` (RABAX) | `RS_CUA_INTERNAL_WRITE` BIV zorunlu → FETCH'ten gelen biv'i geçir. |
| GUI status Almanca | SOAP-RFC çağrısında `sap-language` yok → logon-default dil. `sap-language=TR` geç. |
| Geri/Çıkış çalışmıyor | Donör status jenerik `&F03/&F15/&F12` map'liyor → program PAI `BACK/EXIT/CANCEL` bekliyor. pfk fcode'larını re-map et. |

### 12.7 `423` push'ta — obje o TRANSPORT'a kayıtlı değil (lock verilir, değişiklik reddedilir)

**Belirti:** Bir obje (tipik olarak CLASS) push edilirken **`423 InvalidLockHandle`**. Lock çağrısı
**başarılı** görünür, handle döner — ama PUT reddedilir. Aynı oturumda **başka objeler sorunsuz
push edilir** (bu yüzden "araç bozuk" sanılır).

**Kök sebep:** Objeyi, **kayıtlı olmadığı** bir transport (`corrNr`) ile değiştirmeye çalışmak.
SAP bu durumda kilidi VERİR ama `MODIFICATION_SUPPORT=NoModification` der ve `CORRNR` **boş** döner;
`423` bunun türevidir. Sık senaryo: elde bir **görev (S)** numarası vardır (`DS4K9xxxxx`), ama obje
**üst istek (K)** altında ya da **başka bir görevde** kayıtlıdır.

**Teşhis (tek sorgu, kesin):**
```sql
SELECT trkorr, pgmid, object, obj_name FROM e071 WHERE obj_name = '<OBJE>'
```
Kullandığın `corrNr` bu listede YOKSA sebep budur. (Ölçülmüş vaka: aynı oturumda `..._CL_FLOW_TEXTS`
kullanılan görevde kayıtlıydı → geçti; `..._CL_AMBTAK_DOCU_RUN` yalnız üst istek + başka görevde
kayıtlıydı → 423.)

**ÇÖZÜM — `corrNr`'ı SABİT YAZMA, LOCK YANITINDAN OKU.**
`lock_object()` etkin transport'u `_last_lock_effective_transport`'a koyar (docstring'i bunu uyarır).
Kanonik kalıp:
```python
lock_handle = adt.lock_object(OBJ_URL, transport=TRANSPORT)
eff = getattr(adt, '_last_lock_effective_transport', None) or TRANSPORT
params = {'lockHandle': lock_handle, 'corrNr': eff}     # ← eff, TRANSPORT DEĞİL
```
⛔ **`corrNr = TRANSPORT` (sabit) yazan her script bu hataya açıktır.** Bugüne kadar iki kez ısırdı.

**⛔ YANLIŞ TEŞHİS UYARISI — bu tuzağa iki kez düşüldü:**
Semptom `register_object_in_transport()`'un CSRF ön-alımına yıkıldı (*"`self.csrf_token`'ı eziyor"*).
**YANLIŞ.** ① O ön-alım **kasıtlı ve zorunlu**: SAP `/cts/*` uçlarında `/discovery` token'ını
yanıltıcı bir **403** ile reddeder. ② Fonksiyonun kendisi **"Bug 19"** düzeltmesidir (R3TR ön-kaydı
olmadan CTS **her include için ayrı K+S transport** açıyordu) — kaldırmak o hatayı geri getirir.
③ `CORRNR` boş dönmesi kodda zaten **hata değil `[INFO]`** sayılır (`sap_adt_lib.py:2384-2387`),
yani "CORRNR yok ⇒ enqueue ölü" zinciri **kodun kendi davranışıyla çelişir**.
⇒ **`register_object_in_transport`'a DOKUNMA.**

**Kontrol grubu doğru eksende kurulmalı (PATTERN #19):** "sınıf ↔ include" değil,
**"çalışan sınıf ↔ patlayan sınıf"**. Yanlış eksen, kök sebebi 10 gün boyunca gizledi.

**📌 Tarihçe / bu kaydın var oluş sebebi:** Aynı kalıp **2026-07-30**'da çözülmüştü
(proje `SESSION_NOTES`'ta kayıtlı) ama **core'a terfi etmedi (T1 kaçtı)** ⇒ 2026-08-09'da
**yanlış teşhisle yeniden keşfedildi** ve paylaşılan araca neredeyse yanlış bir düzeltme yapılacaktı.
Ders: *proje notunda çözülen ADT kalıbı core'a terfi etmezse, çözülmemiş sayılır.*
