---
applies_to: [s4_private]
layer: L3
scope: project-wide
type: playbook
applies-to: backend
last-updated: 2026-06-02
status: active
purpose: Function Group (FUGR) ve Function Module (FM) ADT pattern'leri
---

# Function Group (FUGR) ve Function Module (FM) — ADT Pattern'leri

> Bu dosya FUGR/FM'in **genel** ADT yaratma/push/activate pattern'i. C1 (Dynpro üreten
> RFC FM) yalnızca bir **örnek** — en altta. Canlı kanıt: <SYSTEM_ID> (DEV), 2026-06-02
> (ZSD000_FG_SCREEN_GEN / ZSD000_FM_SCREEN_GEN) + mevcut ZSD001/ZSD001 FM'leri.

## Referans

- Kanonik metotlar: `sap_adt_lib.SAPADTClient.create_function_group / create_function_module / set_function_module_source`
- CLI: [`scripts/create_function_group.py`](../scripts/create_function_group.py), [`scripts/create_function_module.py`](../scripts/create_function_module.py)
- Genel push/lock/activate temeli: [`adt-foundation.md §3.2`](adt-foundation.md)
- Canlı çalışan örnek source'lar: `ERP/SD/ZSD001_CLC/functions/*.abap`, `ERP/SD/ZSD001_CLC/functions/*.abap`, `ERP/SD/ZSD000_CLC/functions/ZSD000_FM_SCREEN_GEN.func.abap`

---

## 1. FUGR Yaratma — ÇALIŞAN YÖNTEM

**Endpoint:** `POST /sap/bc/adt/functions/groups`
**Content-Type/Accept:** `application/vnd.sap.adt.functions.groups.v2+xml`
**Query:** `corrNr=<transport>` (zorunlu)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<group:abapFunctionGroup xmlns:group="http://www.sap.com/adt/functions/groups"
                         xmlns:adtcore="http://www.sap.com/adt/core"
                         adtcore:name="ZXXX_FG_FOO"
                         adtcore:description="..."
                         adtcore:masterLanguage="TR">
  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/zxxx_clc"
                      adtcore:type="DEVC/K" adtcore:name="ZXXX_CLC"/>
</group:abapFunctionGroup>
```

- **CSRF-retry ŞART** (`_request_with_csrf_retry`) — bayat token → 403; tek-atış `session.post` 403 yer.
- **Idempotent:** zaten varsa bu sistem `405 AlreadyExists` yerine **`400`** döndürebilir → mevcut kabul (yeniden yaratma normaldir, hata değil).
- ADR 0005 D: `masterLanguage="TR"` + TR login zorunlu.

---

## 2. FM Yaratma + İmza + Gövde — ÇALIŞAN YÖNTEM

Üç parça: (a) shell create, (b) full source push (imza satır-içi + gövde), (c) activate.
`set_function_module_source()` (b)+(c)'yi sarar.

### 2a. Shell create

**Endpoint:** `POST /sap/bc/adt/functions/groups/<fg>/fmodules`
**Accept:** `...functions.fmodules.v2+xml` · **Content-Type:** `...functions.fmodules+xml` · **Query:** `corrNr`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<fmodule:abapFunctionModule xmlns:fmodule="http://www.sap.com/adt/functions/fmodules"
                            xmlns:adtcore="http://www.sap.com/adt/core"
                            adtcore:name="ZXXX_FM_FOO"
                            adtcore:description="..."
                            adtcore:masterLanguage="TR">
</fmodule:abapFunctionModule>
```

- **Sadece** `name`+`description`+`masterLanguage`. Başka attribute ekleme (aşağı bak).
- **CSRF-retry ŞART.** Idempotent: "zaten var" → bu sistemde `400 ExceptionResourceAlreadyExists` (mevcut kabul).

### 2b. İmza + gövde push (TEK source)

⭐ **İmza, SE37-stili `*"` comment-block DEĞİL, satır-içi ABAP cümleleridir.** `FUNCTION <name>`
satırından hemen sonra `IMPORTING/EXPORTING/CHANGING/TABLES/EXCEPTIONS ... .` yazılır; sonra gövde; `ENDFUNCTION.`.

```abap
FUNCTION zxxx_fm_foo
  IMPORTING
    VALUE(iv_in) TYPE string
  EXPORTING
    VALUE(ev_out) TYPE i.

  ev_out = strlen( iv_in ).
ENDFUNCTION.
```

İmza source'tan set edilir → **imza için SE37 GEREKMEZ.** (Kanıt: ZSD001_FM_SO_CREATE.)

**Push mekaniği** (`set_function_module_source` içinde — `adt-foundation.md §3.2`):
1. `self.session.headers['X-sap-adt-sessiontype']='stateful'` (lock'un PUT'a kadar yaşaması için).
2. `fetch_csrf_token(force_refresh=True)`.
3. **LOCK:** `POST .../fmodules/<fm>?_action=LOCK&accessMode=MODIFY`, header `X-sap-adt-corrNr=<tr>`, Accept `...adt.lock.v1+xml` → cevaptan `LOCK_HANDLE` çek. (Lock endpoint = `.../fmodules/<fm>`, `/source/main` DEĞİL.)
4. **PUT:** `PUT .../fmodules/<fm>/source/main?lockHandle=<h>&corrNr=<tr>`, Content-Type `text/plain; charset=utf-8`, body=source.
5. **UNLOCK:** `POST .../fmodules/<fm>?_action=UNLOCK&lockHandle=<h>` (finally).

### 2c. Activate

- `activate_object(FM.upper(), '.../fmodules/<fm>')` — ayrı çağrı (CSRF-retry'li).
- ⚠️ **Aktivasyonu lock-session'ının CSRF token'ıyla yapma** → `403`. Fresh token gerekir; `activate_object()` bunu halleder. Manuel endpoint: `POST /sap/bc/adt/activation?method=activate&preauditRequested=true`, body `adtcore:objectReferences` (type=`FUNC/FF`).

### Kanonik kod (helper ile)

```python
c = SAPADTClient()
c.create_function_group('ZXXX_FG_FOO', '...', 'ZXXX_CLC', transport=TR)   # idempotent
c.create_function_module('ZXXX_FM_FOO', 'ZXXX_FG_FOO', '...', transport=TR)
# (RFC gerekiyorsa: SE37'de "Remote-Enabled Module" tek-tık — bkz. §3)
src = open('.../functions/ZXXX_FM_FOO.func.abap', encoding='utf-8').read()
res = c.set_function_module_source('ZXXX_FM_FOO', 'ZXXX_FG_FOO', src, transport=TR, activate=True)
# res['activation']['success'] == True, errors == []
```

---

## 3. RFC-enable (Remote-Enabled Module)

- ⛔ **ADT create attribute'tan YAPILMIYOR:** create XML'e `fmodule:processingType="remoteEnabled"` → `400 ExceptionInvalidData "Unexpected Case in Branch"`.
- ✅ **Bilinen çalışan yol:** SE37'de "Remote-Enabled Module" radyo (bir kerelik manuel tek-tık). Sonra metadata GET `processingType="rfc"` gösterir.
- ❓ **TEST EDİLMEDİ:** post-create **metadata PUT** ile (`...fmodules.v3+xml`, `processingType="remoteEnabled"`, lock'lu) RFC-enable yapılabilir mi — denenmedi (C1'de source-push önce patladığı için sıraya gelmedi). Gerekirse dene; çalışırsa buraya ÇALIŞAN olarak taşı, manuel adımı kaldır.

---

## 4. Doğrulama / Okuma

- **FM source oku:** `get_object_source('/sap/bc/adt/functions/groups/<fg>/fmodules/<fm>')` (path ver, full URL DEĞİL — full URL verirsen lib `self.url`'i tekrar ekler, "Failed to parse" double-URL).
- **Metadata (processingType/version):** `GET .../fmodules/<fm>` Accept `...fmodules.v3+xml` → `processingType`, `version`, `masterLanguage`, `releaseState`.
- ⚠️ **MCP `adt_get object_type='func'` GÜVENİLMEZ:** mevcut FM'e bile `exists:false` döndürür (group-resolution bug; standart RPY_DYNPRO_INSERT'te de yanıltıcı). Aynı şekilde `adt_lock_check` func. → **Varlık kontrolü için `adt_search_objects` veya group-qualified metadata GET kullan.** **KAPSAM:** bu sorun YALNIZ `object_type='func'`a özgüdür (FM group-resolution); genel `adt_get` DDIC-okuması güvenilirdir (DTEL/DOMA/TABL/struct/ttyp KÖK-FIX 2026-06-16, hafıza `feedback_adt-get-ddic-read-fixed`) — "adt_get genelde güvenilmez" algısı YARATMA.

---

## 5. DENENEN VE BAŞARISIZ YOLLAR (canlı, 2026-06-02)

| Deneme | Hata | Doğru yol |
|---|---|---|
| FG/FM create tek-atış `session.post`+`fetch_csrf_token` | `403` | Bayat CSRF token → `_request_with_csrf_retry` (force-refresh+1 retry). |
| FM create XML'e `processingType="remoteEnabled"` attribute | `400 "Unexpected Case in Branch"` | Create attribute değil → RFC-enable SE37 tek-tık (§3). |
| İmzayı `*"` comment-block olarak push | `400 "Parameter comment blocks are not allowed"` | İmzayı **satır-içi ABAP cümleleri** yaz (§2b). |
| `set_object_source()` ile FM push (4 transport-retry + ETag GET) | `423 InvalidLockHandle` | Retry/ETag stateful lock'u bozuyor → §2b sıkı lock→PUT→unlock (tek session). `set_object_source` FM'de KULLANMA. |
| Aktivasyonu lock-session CSRF token'ıyla yapmak | `403` | `activate_object()` (fresh CSRF-retry) ile ayrı çağır (§2c). |
| placeholder `adt-fugr-functions.md`'e bakıp "pattern yok"/"yapılamaz" demek | patinaj (saatler) | Çalışan pattern `adt-foundation.md §3.2` + repo'daki çalışan `.abap`'taydı → **FM işi öncesi onları oku** (lessons-learned PATTERN #7). |

---

## 6. ÖRNEK: C1 — Dynpro + GUI status üreten RFC sarıcı FM (TAM DOĞRULANDI 2026-06-03)

> 📘 **Adım-adım kullanım kılavuzu:** [`howto-dynpro-gui-status-generation.md`](howto-dynpro-gui-status-generation.md). Bu bölüm derin iç-mekanik referansıdır.

`ZSD000_FM_SCREEN_GEN` (RFC) tek çağrıda hedef programa **(1) boş Dynpro (screen)** + **(2) GUI status + titlebar** üretir; `/sap/bc/soap/rfc` (dialog context) üzerinden çağrılır. Sonuç: `screen rc=2 (zaten var); status(STAT0100+TIT0100) rc=0` → `ZSD000_P_ALV_TEMP1` syntax valid + **aktif**.

- İmza: IMPORTING `IV_PROGRAM SCRHPROG` / `IV_DYNPRO SCRFDYNNR`(`0100`) / `IV_TRANSPORT TRKORR` opt / **`IV_TITLE RSMPE_TITT-TEXT`(`'Liste'`)** (titlebar+dynpro açıklaması; generic) / **`IV_SCREEN_TYPE CHAR10`(`'DOCKING'`)** → 2 layout: `DOCKING` (container yok, program docking ekler) · `CONTAINER` (1 custom control = `IV_CC_NAME`, vars. `CC_ALV`). *(Split AYRI tip değil → CONTAINER + kodda `cl_gui_splitter_container`.)* / **`IV_CC_NAME SCRCNAME`(`'CC_ALV'`)** / **`IV_MODE CHAR10`(`'WRITE'`)** (`'READ'`→sadece dynpro container+CUA title/fun oku, yazma yok) / **`IV_RECREATE CHAR1`** (`'X'`→mevcut ekranı RS_SCRP_DELETE+INSERT ile yeniden kur; flow/container/status değişimini uygular); EXPORTING `EV_RC I` / `EV_MESSAGE STRING`. ABAP'ta `cl_gui_custom_container( container_name = '<name>' )` ile bağlanır.
- **(1) Screen:** `RPY_DYNPRO_INSERT` — header `rpy_dyhead` (type='N', nextscreen=kendi), flow_logic `rpy_dyflow` (PBO/PAI MODULE satırları), containers/fields boş (docking ALV programatik bağlanır).
- **(2) Status:** `RS_CUA_INTERNAL_FETCH`(donör=standart `SAPLKKBL` status `STANDARD`) → tablolarda **bloat azalt** (`DELETE sta/set WHERE <> donör`; **`tit` tamamen REFRESH → sadece `TIT0100`** yoksa donörün 16 titlebar'ı 003/800/850/DYN/FIL... programa sızar) → status kodunu `STANDARD`→`STAT0100` rename (sta+set) → `RS_CUA_INTERNAL_WRITE`(program=hedef, tr_key obj_type=PROG/sub_type=CUAD) → ⚠️ **`RS_CUA_GENERATE`(objectname=hedef) ŞART** (WRITE yalnız tanımı yazar; load'u üretmez → runtime `00264 "GUI status ... not generated"`). Standart sadece OKUNUR, yazma Z'ye → ADR 0005 OK. Sahibi biz → sonra fonksiyon kodu eklenebilir.

### KRİTİK: dialog-context + SOAP-RFC (classrun ÇALIŞMAZ)

| Konu | Not |
|---|---|
| **Neden SOAP-RFC, classrun değil** | Hem `RPY_DYNPRO_INSERT` hem `RS_CUA_INTERNAL_WRITE` **dialog context** ister. `adt_classrun` → `400 "Session Timed Out"`. → RFC-enabled FM'i `/sap/bc/soap/rfc` (dialog) üzerinden çağır. |
| **SOAP-RFC çağrı** | `POST /sap/bc/soap/rfc?sap-client=<c>`, basic auth, `Content-Type: text/xml`, `SOAPAction:""`, envelope ns `urn:sap-com:document:sap:rfc:functions`, body `<urn:FM_NAME><PARAM>val</PARAM></urn:FM_NAME>`. Cevap `<EV_*>` döner. |
| **`RS_CUA_INTERNAL_WRITE` BIV zorunlu** | FETCH'te `biv` OPTIONAL ama WRITE'ta **zorunlu** (`mandatory parameter BIV was not filled` → RABAX). FETCH'ten gelen `biv`'i WRITE'a geçir. |
| **classrun app-server load-cache** | classrun bir class'ı bir kez yükleyince, push+activate sonrası bile **eski load'u** çalıştırabilir (delete+recreate'e rağmen). → iterasyonda **yeni class adı** kullan ya da bu kanaldan değil FM/SOAP-RFC'den git. |
| **tr_key (RS_CUA_INTERNAL_WRITE)** | `obj_type='PROG'`, `obj_name=prog`, `sub_type='CUAD'`, `sub_name=prog`, `devclass=paket`. |
| **WRITE ≠ generate (hata 00264)** | `RS_CUA_INTERNAL_WRITE` yalnız CUA tanımını yazar; runtime load üretmez → status Menu Painter'da görünür ama çalışınca `00264 "... durumu eksik / not generated"`. → WRITE sonrası **`RS_CUA_GENERATE`(objectname=prog, without_messages/checks='X')** çağır (dialog context). |

**C1 DURUMU: TAMAM.** screen 0100 + STAT0100 + TIT0100 üretildi, `ZSD000_P_ALV_TEMP1` aktif. (İyileştirme: STAT0100 şu an SAPLKKBL fonksiyon havuzunu miras alır; gerekirse SE41'de sadeleştir/genişlet.)

### 6.1 Ekranda CONTAINER / kontrol alanı üretimi (RPY_DYNPRO_INSERT `containers`)

`RPY_DYNPRO_INSERT`'in `containers` (TABLES, tip `DYCATT_TAB`, satır **`RPY_DYCATT`**) parametresi ile ekranda **konumlu+boyutlu kontrol alanları** üretilebilir. Boş Dynpro (docking ALV) yerine ekranda **belirli yer/boyutta** kontrol (ALV, HTML, header alanları, tablo control, tabstrip) gerektiğinde kullan.

**`RPY_DYCATT` (container) anahtar alanları:**
| Alan | Anlam |
|---|---|
| `type` (dom. SCRCTYPE) | Container tipi — değerler ↓ |
| `name` | Container/alan adı (ekranda referans) |
| `element_of` | Üst container (iç içe) |
| `line` / `column` | Konum (sol-üst köşe) |
| `length` / `height` | Boyut (genişlik / yükseklik) |
| `cu_cc_name` | **Custom control adı** — `CREATE OBJECT cl_gui_custom_container EXPORTING container_name = '<cu_cc_name>'` ile eşleşir |
| `loop_*` | Step loop satır/blok/gösterim |
| `tc_*` | Table control (başlık/header/seçilebilir satır-kolon/sabit kolon/config) |
| `c_resize_*` / `c_scroll_*` / `c_*_min` | Resize / scroll / min boyut |

**`type` (SCRCTYPE) değerleri:** `CUST_CTRL` (**Custom Control** → cl_gui_custom_container: ALV/HTML/resim host), `SUBSCREEN` (subscreen alanı), `TABLE_CTRL` (table control), `STRIP_CTRL` (tabstrip), `RADIOGROUP`, `LOOP` (step loop), BOX/frame (gruplama).

**`fields_to_containers` (tip `DYFATC_TAB`, satır `RPY_DYFATC` = `cont_type`+`cont_name`+include `RPY_DYFATT`):** bir container'a yerleştirilecek **alanları** (input/output, label) tanımlar — ör. header seçim alanları, subscreen içi alanlar.

**Ne zaman hangisi:**
- **Docking container** (mevcut C1 default; `containers` boş): tam-ekran liste, en basit, ekran elemanı gerekmez → tek ALV liste programları.
- **CUST_CTRL üret**: ALV'yi ekranda **belirli yer/boyutta** istediğinde — header alanları + altta ALV, split-screen, birden çok kontrol, tabstrip içi ALV. `containers`'a `type='CUST_CTRL' name=.. line/column/length/height=.. cu_cc_name='CC_ALV'` satırı ekle → ABAP'ta `cl_gui_custom_container( container_name = 'CC_ALV' )`.
- **SUBSCREEN/TABLE_CTRL/STRIP_CTRL**: modüler ekran / klasik table control / sekmeli ekran gerektiğinde.

> Üretim mekaniği screen ile aynı (§6: RFC FM + SOAP-RFC, dialog context). `ZSD000_FM_SCREEN_GEN` `IV_SCREEN_TYPE`'a göre `containers` doldurur: **DOCKING** boş / **CONTAINER** 1 custom control.

> ⭐ **SPLIT SCREEN = AYRI EKRAN TİPİ DEĞİL.** Tek custom control (CONTAINER, CC_ALV) + **programda `cl_gui_splitter_container`**: `NEW cl_gui_splitter_container( parent = go_cc rows = 2 columns = 1 )` → `get_container( row=1 column=1 )` üst, `row=2` alt → her hücreye ALV (sürükle-ayraç). Yani FM split için özel bir şey YAPMAZ; CONTAINER üret, bölmeyi kodda yap. Örnek: `ZSD000_P_ALV_TEMP3` (üst VBAK / çift-tık → alt VBAP master-detail). (`set_row_height(id height)` satır oranı.)

### 6.1.1 ⭐ CUST_CTRL üretiminde KANITLANMIŞ değerler (TEMP2 manuel düzeltmesinden)

İlk üretimde CUST_CTRL'i `element_of` boş + küçük boyut (H=18 W=118, screen 20x120) verdim → çalıştı ama container küçüktü. Kullanıcı SE51'de düzeltti; `RPY_DYNPRO_READ` ile okunan **doğru** değerler:

| Alan | Değer | Not |
|---|---|---|
| Screen `lines`/`columns` | **200 / 255** | Tam boyut → container/ALV pencereyi doldurur (20x120 küçük kalıyordu) |
| CUST_CTRL `element_of` | **BOŞ bırak** | ⚠️ RPY INSERT'te auto-SCREEN'e bağlar (READ'de `el=SCREEN` görünür). Açıkça `'SCREEN'` verirsen INSERT `illegal_field_value` (rc=6) — SCREEN satırı container tablosunda yok. (Önceki "element_of='SCREEN' zorunlu" notu YANLIŞTI.) |
| CUST_CTRL `line`/`column` | `1` / `1` | Sol-üst |
| CUST_CTRL `height`/`length` | **`200` / `255`** (tam ekran) | Split de aynı tek CC; bölme kodda (`cl_gui_splitter_container`), ekrana 2. container KOYMA |
| CUST_CTRL `c_resize_v`/`c_resize_h` | **`'X'` / `'X'`** | ⚠️ ZORUNLU — control pencereyle dikey+yatay RESIZE olur. Set edilmezse control SABİT boyutta kalır → ALV pencereyi doldurmaz ("bittiği yerden sonra devam eder"). |
| CUST_CTRL `c_line_min`/`c_coln_min` | **`1` / `1`** | Min satır/kolon (resize ile birlikte). |

> **Kural (bundan sonra):** screen+container üretirken **screen 200x255 + CUST_CTRL `element_of` BOŞ + ekranı dolduran boyut + `c_resize_v`/`c_resize_h`='X' + `c_line_min`/`c_coln_min`=1**. Resize set edilmezse control sabit kalır (TEMP3 manuel düzeltmesinden öğrenildi). `ZSD000_FM_SCREEN_GEN` bu değerleri kullanır.

### 6.1.2 Status fcode/title + ESC/exit (KANITLANMIŞ ÇALIŞAN) + screen recreate

⭐ **TOOLBAR/MENÜ TEMİZLİĞİ — KRİTİK AYRIM (kanıtlanmış):**
- ✅ **`men`/`mtx` (menü bar) + `but` (application toolbar) REFRESH** → görünür menü+toolbar gider. **`act` (aktif fonksiyon listesi) KORUNUR** → fonksiyonlar GEÇERLİ kalır. `adm-mencode` + `sta-butcode` CLEAR (tutarlılık). Sonuç: temiz ekran (MEN=0 BUT=0) + çalışan butonlar. `fun`/`pfk` (185/865) iç havuz olarak kalır (görünmez, zararsız).
- ⛔ **`act`/`actcode`'u TEMİZLEME** → BACK/EXIT/CANCEL **GEÇERSİZ** olur → runtime **`00256 "Geçerli bir işlev seçin"`** (buton tepkisiz). Fonksiyon geçerliliği `act`'a bağlı; `set`/`pfk` tek başına yetmez. (Bu hata 3-4 kez patinaja yol açtı.)
- ALV grid'in KENDİ toolbar'ı (CL_GUI_ALV_GRID: sırala/filtre/Excel) ayrıdır, etkilenmez.

**ÇALIŞAN status reçetesi (`ZSD000_FM_SCREEN_GEN`):**
- `tit` REFRESH → yalnız `TIT0100` (✅ title'lar status'tan bağımsız → GÜVENLİ prune; tek istisna).
- `pfk` re-map: pfno `03`→`BACK`, `15`→`EXIT`, `12`→`CANCEL` (donör jenerik `&F03/&F15/&F12` yerine; bu kodlar donör fun'ında ZATEN var → geçerli).
- `fun`/`set`: BACK/EXIT/CANCEL yoksa ekle (per-function guard; donörde BACK/EXIT var, CANCEL yok).
- BACK/EXIT/CANCEL `fun-type` → **NORMAL'e zorla** (`CLEAR <fun>-type`): donörde `EXIT type='E'` gelir; AT EXIT-COMMAND modülü olmadan type-E komut işlenmez (buton tepkisiz). Normal → `user_command_0100` yakalar.
- Diğer donör tabloları (act/men/but/...) DOKUNMA.

**Her şey IV_DYNPRO'ya göre DİNAMİK (FM kodu ekran başına değişmez):** screen no + flow modülleri (`MODULE status_<dynnr>` / `user_command_<dynnr>`) + GUI status (`STAT<dynnr>`) + titlebar (`TIT<dynnr>`). Programdaki `CALL SCREEN <n>` + `MODULE status_<n>/user_command_<n>` + `SET PF-STATUS 'STAT<n>'` + `SET TITLEBAR 'TIT<n>'` aynı numarayı kullanmalı. `IV_MODE`: `WRITE`(üret) / `READ`(oku) / `DELETE`(`RS_SCRP_DELETE`). Taze üretim (0200) sıfırdan kusursuz doğrulandı (resize + dinamik isimler, manuel fix yok).

**ESC = çıkış (ÇALIŞAN):** Nav fonksiyonları NORMAL type + `user_command_0100` (CASE sy-ucomm WHEN BACK/EXIT/CANCEL → LEAVE PROGRAM). **ESC = F12 = CANCEL** → user_command yakalar → çıkış. (type='E'+AT EXIT-COMMAND yolu DENENDİ ve BAŞARISIZ: generated ekranda OK command-field yok → type-E komut yakalanamadı, butonlar tepkisiz. OK-field üretimi gerekir; şimdilik normal-type yeterli, ESC zaten F12 ile çalışıyor.)

**Flow/container değişimini mevcut ekrana uygulamak:** `RPY_DYNPRO_INSERT` mevcut ekranı overwrite ETMEZ (already_exists rc=2). `RPY_DYNPRO_DELETE` YOK → **`RS_SCRP_DELETE`** (`with_popup=space suppress_checks='X' corrnum=tr`) ile sil, sonra INSERT (`IV_RECREATE='X'`). ⚠️ DELETE sonrası INSERT patlarsa (örn. `element_of='SCREEN'` → rc=6) ekran kaybolur → INSERT değerlerini önce doğru bil (element_of BOŞ).

---

## İlgili

- [`adt-foundation.md`](adt-foundation.md) §3.2 — Genel FM push/lock/activate temeli
- [`adt-classes.md`](adt-classes.md) — Class push/activate (benzer lock pattern)
- [`lessons-learned.md`](lessons-learned.md) — PATTERN #7 (placeholder tuzağı)
- [`governance/deferred-triggers.md`](../governance/deferred-triggers.md) — C1 register satırı
