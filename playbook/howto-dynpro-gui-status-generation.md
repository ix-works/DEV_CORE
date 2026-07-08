---
applies_to: [s4_private]
layer: L3
scope: project-wide
type: howto
applies-to: backend (classic dialog)
last-updated: 2026-06-03
status: active
purpose: Klasik Dynpro ekranı + GUI status'u AI'ın RFC FM ile (SOAP-RFC, dialog context) üretmesi
---

# HOW-TO — Klasik Dynpro Ekranı + GUI Status Üretimi (RFC, AI-otomatik)

> **Amaç:** Klasik bir ABAP programına (report/module pool) **Dynpro ekranı + GUI status + titlebar**
> üretmek — operatöre SE51/SE41 GEREKMEDEN, tamamen AI/REST üzerinden. Bunu yapan üreteç:
> **`ZSD000_FM_SCREEN_GEN`** (RFC-enabled, FG `ZSD000_FG_SCREEN_GEN`), `/sap/bc/soap/rfc` (dialog) üzerinden çağrılır.
>
> Bu dosya **adım-adım kullanım kılavuzudur.** Derin referans/iç mekanik: [`adt-fugr-functions.md`](adt-fugr-functions.md) §6.
> Üretimden önce: [`checklists/classic-dialog-creation.md`](checklists/classic-dialog-creation.md) §Faz 3 (CLC-SCR1..5).

---

## 0. Ne zaman kullanılır

Klasik dialog programı (ALV liste, master-detail, header+liste) yazıyorsun ve programın bir
**ekrana (`CALL SCREEN`)** + **GUI status (PF-STATUS)** + **titlebar**'a ihtiyacı var. RAP/Fiori değil,
klasik SE80-tarzı program. ALV genelde bu ekrandaki bir container'a/docking'e bağlanır.

## 1. Neden SOAP-RFC, neden classrun DEĞİL (mimari)

`RPY_DYNPRO_INSERT` ve `RS_CUA_INTERNAL_WRITE` **dialog context** ister. `adt_classrun` ile çağırırsan
`400 "Session Timed Out"` alırsın. Çözüm: **RFC-enabled** FM'i **SOAP-RFC** kanalından çağır:

```
POST /sap/bc/soap/rfc?sap-client=<client>
  Authorization: Basic ...
  Content-Type: text/xml
  SOAPAction: ""
  Body (envelope ns urn:sap-com:document:sap:rfc:functions):
    <urn:ZSD000_FM_SCREEN_GEN>
      <IV_PROGRAM>ZSD000_P_ALV_TEMP1</IV_PROGRAM>
      <IV_DYNPRO>0100</IV_DYNPRO>
      <IV_TRANSPORT>...</IV_TRANSPORT>
      <IV_TITLE>Liste</IV_TITLE>
      <IV_SCREEN_TYPE>DOCKING</IV_SCREEN_TYPE>
    </urn:ZSD000_FM_SCREEN_GEN>
  Cevap: <EV_RC>, <EV_MESSAGE>
```

> ⚠️ `sap-language=TR` ile çağır (yoksa GUI metinleri Almanca/boş gelir — ADR 0005-D).

## 2. FM imzası (`ZSD000_FM_SCREEN_GEN`)

| Parametre | Tip | Default | Anlam |
|---|---|---|---|
| `IV_PROGRAM` | `SCRHPROG` | — | Hedef program |
| `IV_DYNPRO` | `SCRFDYNNR` | `0100` | Ekran no — **her şey buna göre dinamik** (aşağı bak) |
| `IV_TRANSPORT` | `TRKORR` | opt | Transport |
| `IV_TITLE` | `RSMPE_TITT-TEXT` | `'Liste'` | Titlebar + dynpro açıklaması (TR) |
| `IV_SCREEN_TYPE` | `CHAR10` | `'DOCKING'` | `DOCKING` / `CONTAINER` (split = CONTAINER + kod) |
| `IV_CC_NAME` | `SCRCNAME` | `'CC_ALV'` | Custom control adı (CONTAINER tipinde) |
| `IV_MODE` | `CHAR10` | `'WRITE'` | `WRITE`(üret) / `READ`(oku) / `DELETE`(`RS_SCRP_DELETE`) |
| `IV_RECREATE` | `CHAR1` | `' '` | `'X'` → mevcut ekranı sil+yeniden kur |
| `EV_RC` / `EV_MESSAGE` | `I` / `STRING` | — | Sonuç (rc=0 OK, rc=2 zaten var) |

**Dinamik isimlendirme:** `IV_DYNPRO=<n>` → ekran `<n>`, flow modülleri `MODULE status_<n>`/`user_command_<n>`,
GUI status `STAT<n>`, titlebar `TIT<n>`. **FM kodu ekran başına DEĞİŞMEZ** — sadece IV_DYNPRO değişir.

## 3. Adım adım

### Adım A — Programda iskeleti yaz (include'lara bölünmüş — std 06 §1)
Program tarafı, üretilecek ekran/status numarasıyla **eşleşmeli**:
```abap
CALL SCREEN 0100.

MODULE status_0100 OUTPUT.
  SET PF-STATUS 'STAT0100'.
  SET TITLEBAR  'TIT0100'.
  " ... ALV container'a bağla (docking veya CC_ALV)
ENDMODULE.

MODULE user_command_0100 INPUT.
  CASE sy-ucomm.
    WHEN 'BACK' OR 'EXIT' OR 'CANCEL'. LEAVE PROGRAM.   " ESC = F12 = CANCEL
  ENDCASE.
ENDMODULE.
```

### Adım B — FM'i çağır (ekran + status üretimi tek çağrı)
SOAP-RFC ile `ZSD000_FM_SCREEN_GEN`'i çağır (§1 envelope). İçinde olan:
- **(1) Screen:** `RPY_DYNPRO_INSERT` — header (type='N', nextscreen=kendi), flow_logic (PBO/PAI MODULE satırları), `containers` (IV_SCREEN_TYPE'a göre boş/CUST_CTRL).
- **(2) Status:** `RS_CUA_INTERNAL_FETCH`(donör `SAPLKKBL`/`STANDARD`) → prune (§5) → rename `STANDARD`→`STAT<n>` → `RS_CUA_INTERNAL_WRITE`(tr_key PROG/CUAD) → **`RS_CUA_GENERATE`** (ŞART).

### Adım C — Doğrula
```
EV_RC=0 (veya 2=zaten var) + syntax check + programı çalıştır.
```
`RPY_DYNPRO_READ` ile ekran/container değerlerini, `IV_MODE='READ'` ile CUA title/fun'ı okuyabilirsin.

## 4. Layout tipleri

| Tip | Ne zaman | Nasıl |
|---|---|---|
| **DOCKING** (default) | Tam-ekran tek ALV liste | `IV_SCREEN_TYPE='DOCKING'`, `containers` boş; programda `cl_gui_docking_container` |
| **CONTAINER** | ALV'yi belirli yer/boyutta, header+liste, çoklu kontrol | `IV_SCREEN_TYPE='CONTAINER'`, 1 custom control (`CC_ALV`); programda `cl_gui_custom_container( container_name='CC_ALV' )` |
| **SPLIT** | Master-detail (üst/alt liste) | **AYRI tip DEĞİL** → `CONTAINER` üret + programda `cl_gui_splitter_container` |

### ⭐ CONTAINER üretiminde KANITLANMIŞ değerler (ZORUNLU)
FM bunları otomatik kullanır; manuel CUST_CTRL yaratırsan bu değerleri ver:

| Alan | Değer | Neden |
|---|---|---|
| Screen `lines`/`columns` | **200 / 255** | Container pencereyi doldursun (küçük boyut → ALV kırpılır) |
| CUST_CTRL `element_of` | **BOŞ** | RPY INSERT auto-SCREEN'e bağlar. Açık `'SCREEN'` → `illegal_field_value` (rc=6) |
| `line`/`column` | `1` / `1` | Sol-üst |
| `height`/`length` | **200 / 255** | Tam ekran |
| `c_resize_v`/`c_resize_h` | **`'X'` / `'X'`** | ⚠️ ZORUNLU — yoksa control SABİT, ALV pencereyi doldurmaz |
| `c_line_min`/`c_coln_min` | `1` / `1` | Min satır/kolon |

### SPLIT örnek (programda — FM split için özel bir şey yapmaz)
```abap
go_split = NEW cl_gui_splitter_container( parent = go_cc rows = 2 columns = 1 ).
go_top   = go_split->get_container( row = 1 column = 1 ).   " üst ALV
go_bot   = go_split->get_container( row = 2 column = 1 ).   " alt ALV
" go_split->set_row_height( id = 1 height = 50 ).  " gerekiyorsa oran
```
Örnek: `ZSD000_P_ALV_TEMP3` (üst VBAK / çift-tık → alt VBAP). **Ekrana 2. container KOYMA.**

## 5. GUI status reçetesi — toolbar/menü temizliği (KRİTİK)

FM, donör `SAPLKKBL/STANDARD` status'unu alıp şöyle sadeleştirir:

- ✅ **`men`/`mtx` (menü) + `but` (app toolbar) REFRESH** → görünür menü+toolbar gider. `adm-mencode`+`sta-butcode` CLEAR.
- ✅ **`act` (fonksiyon geçerlilik listesi) KORUNUR.**
- ⛔ **`act`/`actcode` TEMİZLENMEZ** → temizlersen BACK/EXIT/CANCEL **geçersiz** olur → runtime **`00256 "Geçerli bir işlev seçin"`** (buton tepkisiz). *(Bu hata 3-4 kez patinaja yol açtı.)*
- ✅ `tit` REFRESH → yalnız `TIT<n>` (title'lar status'tan bağımsız → güvenli prune).
- ✅ `pfk` re-map: `03`→`BACK`, `15`→`EXIT`, `12`→`CANCEL`.
- ✅ BACK/EXIT/CANCEL `fun-type` → **NORMAL'e zorla** (`CLEAR <fun>-type`); donör `EXIT type='E'` gelir, AT EXIT-COMMAND modülü yoksa komut işlenmez.
- ✅ **WRITE sonrası `RS_CUA_GENERATE` ŞART** — yoksa runtime **`00264 "GUI status not generated"`** (Menu Painter'da görünür ama çalışmaz).

## 6. ESC / çıkış

Nav fonksiyonları NORMAL type + `user_command_<n>` (`CASE sy-ucomm WHEN BACK/EXIT/CANCEL → LEAVE PROGRAM`).
**ESC = F12 = CANCEL** → user_command yakalar. *(type='E' + AT EXIT-COMMAND yolu DENENDİ ve başarısız: generated ekranda OK command-field yok → type-E komut yakalanamadı.)*

## 7. READ / RECREATE / DELETE modları

- **`IV_MODE='READ'`** → yazmadan dynpro container + CUA title/fun okur (denetim).
- **`IV_RECREATE='X'`** → mevcut ekranı `RS_SCRP_DELETE` + INSERT ile yeniden kurar (flow/container/status değişimini uygular). `RPY_DYNPRO_INSERT` overwrite ETMEZ (already_exists rc=2).
- **`IV_MODE='DELETE'`** → `RS_SCRP_DELETE` (`with_popup=space suppress_checks='X' corrnum=tr`). `RPY_DYNPRO_DELETE` YOKTUR.
- ⚠️ DELETE sonrası INSERT patlarsa (örn. `element_of='SCREEN'` → rc=6) ekran kaybolur → INSERT değerlerini önce doğru bil.

## 8. Tuzaklar (hızlı referans)

| Belirti | Sebep / Çözüm |
|---|---|
| `400 Session Timed Out` (classrun) | Dialog context yok → SOAP-RFC kanalı kullan |
| `00256 Geçerli bir işlev seçin` | `act` temizlenmiş → `act` KORU (sadece men/mtx/but REFRESH) |
| `00264 GUI status not generated` | `RS_CUA_GENERATE` çağrılmamış → WRITE sonrası GENERATE ŞART |
| `mandatory parameter BIV` (RABAX) | FETCH'ten gelen `biv`'i WRITE'a geçir |
| Buton tepkisiz | `fun-type='E'` kalmış → NORMAL'e CLEAR et |
| ALV pencereyi doldurmuyor | CUST_CTRL `c_resize_v/h='X'` set edilmemiş |
| INSERT `illegal_field_value` rc=6 | CUST_CTRL `element_of='SCREEN'` verilmiş → BOŞ bırak |
| GUI metinleri Almanca | `sap-language=TR` ile çağır |

---

## İlgili
- [`adt-fugr-functions.md`](adt-fugr-functions.md) §6 — derin iç mekanik / FUGR+FM yaratma
- [`checklists/classic-dialog-creation.md`](checklists/classic-dialog-creation.md) — üretim öncesi checklist (CLC-SCR1..5)
- [`../standards/06-coding-classic-dialog.md`](../standards/06-coding-classic-dialog.md) — klasik dialog kodlama standardı
- [`templates/classic-alv-list.prog.abap`](templates/classic-alv-list.prog.abap) — kanonik inline-ALV template
- Canlı örnekler: `ERP/SD/ZSD000_CLC/functions/ZSD000_FM_SCREEN_GEN.func.abap`, `ERP/SD/ZSD000_CLC/programs/ZSD000_P_ALV_TEMP1/2/3.prog.abap`
