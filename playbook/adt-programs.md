---
applies_to: [s4_private]
layer: L3
scope: project-wide
type: playbook
applies-to: backend
last-updated: 2026-05-14
status: active
---

# ABAP Report (PROG/P)

## 21. ABAP Report (PROG/P) — Aktivasyon Hataları

### 23.1 SELECT-OPTIONS / PARAMETERS İsim Uzunluğu (max 8 karakter)

**Hata:**
```
The SELECT-OPTION name ("SO_INV_NO" here) can be up to eight characters long.
The parameter name ("RB_BY_MAT" here) can be up to eight characters long.
```

**Kural:** SELECT-OPTIONS ve PARAMETERS isimleri **maksimum 8 karakter** olabilir.

**Çözüm — kısa isimler kullan:**
```abap
" YANLIS (9-11 karakter):
SELECT-OPTIONS: so_inv_no FOR ..., so_inv_date FOR ..., so_customer FOR ...
PARAMETERS: rb_by_mat RADIOBUTTON GROUP ..., rb_by_cust RADIOBUTTON GROUP ...

" DOGRU (max 8 karakter):
SELECT-OPTIONS: so_vbeln FOR ..., so_fkdat FOR ..., so_kunag FOR ...
PARAMETERS: rb_mat RADIOBUTTON GROUP ..., rb_cust RADIOBUTTON GROUP ...
```

---

### 23.2 SELECT-OPTIONS FOR Referansı — Tablo-Alan Değil TYPE Kullan

**Hata:**
```
Field "VBRP-VBELN" is unknown.
```

**Sebep:** `SELECT-OPTIONS so_vbeln FOR vbrp-vbeln` yazımı S/4HANA'da TABLES bildirimi olmadan çalışmaz. `TABLES: vbrp, vbrk` gibi bildirimler S/4HANA'da obsolete.

**Çözüm — önce DATA tanımla, FOR ile ona referans ver:**
```abap
" Once DATA tanimla:
DATA: gv_vbeln TYPE vbeln_vf,
      gv_fkdat TYPE fkdat,
      gv_kunag TYPE kunnr,
      gv_vkorg TYPE vkorg,
      gv_matkl TYPE matkl.

" Sonra SELECT-OPTIONS FOR bu data'ya bagla:
SELECT-OPTIONS: so_vbeln FOR gv_vbeln,
                so_fkdat FOR gv_fkdat NO-EXTENSION,
                so_kunag FOR gv_kunag,
                so_vkorg FOR gv_vkorg DEFAULT '1500',
                so_matkl FOR gv_matkl.
```

Custom extension field'lar için rollname'i DD04L'den sorgula, o tipi kullan:
```abap
" VBRP~ZZ1_PRICE_CODE_INV_BDI alaninin rollname'i ZZ1_PRICE_CODE_INV
DATA gv_price TYPE zz1_price_code_inv.
SELECT-OPTIONS so_price FOR gv_price.
```

---

### 23.3 INITIALIZATION'da TEXT-xxx Ataması Yapılamaz

**Hata:**
```
The field "TEXT-B01" cannot be modified.
The field "TEXT-001" cannot be modified.
```

**Sebep:** `TEXT-xxx` sembolleri INITIALIZATION bloğu içinde atanamaz (compile-time constant olarak değerlendirilir).

**Çözüm — SELECTION-SCREEN frame title için serbest değişken kullan:**
```abap
" YANLIS:
SELECTION-SCREEN BEGIN OF BLOCK b_filter WITH FRAME TITLE TEXT-b01.
...
INITIALIZATION.
  TEXT-b01 = 'Filtre Kriterleri'.   " HATA

" DOGRU:
SELECTION-SCREEN BEGIN OF BLOCK b_filter WITH FRAME TITLE tit_flt.
...
INITIALIZATION.
  tit_flt = 'Filtre Kriterleri'.    " CALISIR
```

---

### 23.4 AT SELECTION-SCREEN OUTPUT — screen-text Yok

**Hata:**
```
The data object "SCREEN" does not have a component called "TEXT".
```

**Sebep:** `SCREEN` yapısında `text` alanı yoktur. Radiobutton label ataması için bu yöntem çalışmaz.

**Çözüm:** `AT SELECTION-SCREEN OUTPUT` ile radiobutton metnini değiştirmeye çalışma. Radiobutton label'ı için selection text tablosunu (SE38 → Goto → Text Elements → Selection Texts) kullan ya da bloğu kaldır.

---

### 23.5 CL_SALV_TABLE=>FACTORY — Yanlış IMPORTING Parametre Adı

**Hata:**
```
The formal parameter "SALV_TABLE" does not exist. However, the parameter "R_SALV_TABLE" has a similar name.
```

**Çözüm:**
```abap
" YANLIS:
cl_salv_table=>factory(
  IMPORTING salv_table = lo_salv
  CHANGING  t_table    = lt_result ).

" DOGRU:
cl_salv_table=>factory(
  IMPORTING r_salv_table = lo_salv
  CHANGING  t_table      = lt_result ).
```

---

### 23.6 Extension Field Rollname Tespiti

VBRP, VBAP gibi tablolardaki `ZZ1_*` extension field'ların ABAP type'ını bulmak için:

```python
sql = "SELECT FIELDNAME, ROLLNAME, LENG, DATATYPE FROM DD03L WHERE TABNAME = 'VBRP' AND FIELDNAME LIKE 'ZZ1%'"
# datapreview/freestyle POST ile çalıştır (Accept: application/vnd.sap.adt.datapreview.table.v1+xml)
# ROLLNAME sütunundaki değeri TYPE olarak kullan — _BDI suffix'li field adını değil
```

---

### 23.7 Text-pool push — selection texts + text symbols (blok başlıkları) ✅ ÇALIŞAN YÖNTEM

> **ÇALIŞAN ARAÇ: `scripts/push_textpool.py`** (ZSD001'te kanıtlandı 2026-06-28). C4 deferred-trigger borcunu kapatır. **`adt_push_source` / MCP push_source text-pool'u KAPSAMAZ** — sadece `source/main`. Text element'ler ayrı endpoint + ayrı lock ister.

**Komut:**
```bash
python scripts/push_textpool.py --program ZSD001_P_SOZLESME_KOPYALA --transport <TRANSPORT> \
  --symbols-file <symbols.txt> --selections-file <selections.txt>
```

**Endpoint yapısı** (canlı ZSD001/ZSD001'den doğrulandı):
```
/sap/bc/adt/textelements/programs/<prog>                 → index (type PROG/PX, REPT resource)
/sap/bc/adt/textelements/programs/<prog>/source/symbols     (Content-Type vnd.sap.adt.textelements.symbols.v1)
/sap/bc/adt/textelements/programs/<prog>/source/selections  (... .selections.v1)
/sap/bc/adt/textelements/programs/<prog>/source/headings    (... .headings.v1)
```

**SOURCE format** (canlı GET ile doğrulandı — TAHMİN ETME, kanonik):
- **symbols** (TEXT-bNN blok başlıkları → sembol BNN, 3-harf, padding YOK):
  ```
  @MaxLength:10
  B00=İşlem Türü
                    ← entry'ler arası BOŞ satır (\r\n\r\n)
  @MaxLength:16
  B01=Seçim Kriterleri
  ```
  → `@MaxLength` **PER-ENTRY** (global değil) · değeri = metnin **tam karakter uzunluğu** · entry'ler **boş satırla** ayrılır.
- **selections** (parametre/select-option etiketi): ad **8-haneye sola yaslı** + `=text`, entry'ler boş satırla:
  ```
  P_AUART =Belge Türü          ← 7-char ad + 1 boşluk
  
  P_FILE  =Excel Dosyası       ← 6-char ad + 2 boşluk
  
  RB_RAPOR=Sözleşmeleri Listele ← 8-char ad, boşluk yok
  ```
  → DDIC-türevli etiketi ÖZEL metinle override etmek için `@DDICReference` satırını **yazma** (özel text decouple eder). ADT readback'te alfabetik sıralar (PUT sırası önemsiz).
- **SON entry'den sonra trailing newline YOK** (phantom boş sembol → DS512 reddi).

**6 ZORUNLU CEPHE** (her biri ayrı blocker — hepsi `push_textpool.py`'da çözülü):
1. **CSRF + stateful:** raw `session.put` YETMEZ → `_get_headers()` (X-CSRF-Token + `x-sap-adt-sessiontype:stateful` + sap-client) + `_request_with_csrf_retry()`. Aksi: 403 CSRF + lock kaybı.
2. **Format:** per-entry @MaxLength + boş-satır ayraç + trailing-newline kırp. Aksi: `406 DS512 "Text elements contain errors"`.
3. **lockHandle ZORUNLU:** textelements PUT lockHandle ister; `NO_LOCK_SUPPORT` TOLERE EDİLMEZ → LOUD FAIL. Aksi: `400 SADT_RESOURCE 017`.
4. **Doğru unlock:** `adt.unlock_object()` (stateful+csrf) — raw POST csrf'siz unlock lock'u SIZDIRIR (sonraki run `EU 510 same-user` → NO_LOCK_SUPPORT → SM12'de sil).
5. **REPT-lock (doğru resource):** lock **`/textelements/programs/<prog>`** (REPT) üzerinde — PROGRAM (`/programs/programs/...`, PROG) lock'u DEĞİL. Aksi: `423 SADT_RESOURCE 026 "Resource REPT ... is not locked"`.
6. **PROG/PX EXPLICIT activation + `?version=active` readback (program ZATEN AKTİFSE kritik):** Tek PROG/P-activate YETMEZ. Program zaten aktifse `activate(PROG/P)` **no-op** olur (`activationExecuted=false`) ve inactive PROG/PX'i (text-pool) **PROMOTE ETMEZ** → `selections` ACTIVE'de `=?` (placeholder), `symbols` boş kalır → **ekranda seçim metni/blok başlığı GÖRÜNMEZ** (ama working/inactive readback PUT'lanan metni gösterip YANILTIR — BE-39 textpool varyantı). **Çözüm:** PROG/PX'i DOĞRUDAN seed'le → POST `/sap/bc/adt/activation` objectReference `uri=/sap/bc/adt/textelements/programs/<prog>` `type=PROG/PX` `preauditRequested=true`. **DOĞRULAMA:** readback `?version=active` (working DEĞİL) → `=?`/boş çıkarsa promote olmamış. (ZSD001_P_AMBALAJ_TAKIP 2026-06-28 · [[BE-39]] textpool varyantı.)

**Payload konumu:** paket içinde kalıcı → `ERP/<MOD>/<PKG>/programs/textpool/{symbols,selections}.txt`.

Örnek: `ZZ1_PRICE_CODE_INV_BDI` alanının rollname'i `ZZ1_PRICE_CODE_INV` → `DATA gv_price TYPE zz1_price_code_inv.`

---


