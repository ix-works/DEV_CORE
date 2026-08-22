---
applies_to: [s4_private]
layer: L3
scope: project-wide
type: playbook
applies-to: backend
last-updated: 2026-05-14
status: active
---

# CDS View (DDLS/DF)

## ⛔ CDS-DCL-01 — standart CDS'ten DOĞRUDAN okuma: DCL reddi **0 satır** döner, hata VERMEZ (2026-08-14)

> **Güç: MUST.** `@AccessControl.authorizationCheck: #CHECK` taşıyan bir **standart** CDS view'a
> **doğrudan** eriştiğinde (ABAP `SELECT` · `READ ENTITIES` · SRVD `expose` · OData `$expand`),
> yetkisi olmayan kullanıcıda DCL sorgunun WHERE'ine `N'CDS_Access_Control' = N'DENY'` **enjekte
> eder** ⇒ sorgu **yapısı gereği 0 satır** döner. `sy-subrc` "veri yok" der, **"yetkin yok" demez**;
> exception **atılmaz**. Geliştiricide (geniş yetki) hiç görünmez.
>
> **Kapsam sınırı — ezberlenecek cümle:** implicit access control **yalnız DOĞRUDAN erişimde**
> çalışır. Bir Z view'in `FROM`/`JOIN`/`ASSOCIATION`'ında `#CHECK` standart view kullanmak
> **TEK BAŞINA risk DEĞİLDİR** (dolaylı erişimde DCL değerlendirilmez).
> Kaynak: ABAP CDS – Access Control (`abencds_authorizations`).

**Çare — Open SQL `SELECT` için (canlı derleyicide kanıtlandı 2026-08-14):**

```abap
" DOĞRU — kloz alias'tan ÖNCE gelir
SELECT ... FROM i_packinginstructioncomponent WITH PRIVILEGED ACCESS AS comp
       INNER JOIN i_packinginstructionheader  WITH PRIVILEGED ACCESS AS hdr
               ON hdr~packinginstruction = comp~packinginstruction
  ...
" YANLIŞ — ters sıra derlenmez (abaplint: parser_error; canlı: 400)
"   FROM i_packinginstructioncomponent AS comp WITH PRIVILEGED ACCESS
```

**Uygulanamadığı yerler (ölçülmüş):**

| Yer | Durum |
|---|---|
| Open SQL `SELECT` | ✅ çalışır (yukarıdaki sözdizimi) |
| `READ ENTITIES` (RAP BO) | ⛔ **böyle bir kloz YOK** — başka çare gerekir |
| `@ObjectModel.virtualElement` alanlar | ⛔ **privileged okuma BOŞ getirir** — değer SQL'den değil SADL calc-exit'ten gelir; alttaki table function gövdesi literal `'' as <alan>` döndürebilir. Sessiz-boşu başka bir sessiz-boşla değiştirir. Doğru yol: DCL taşımayan kaynak (metinler için `STXH`/`STXL` + `READ_TEXT`; DDIC tabloları DCL taşımaz) |

⛔ **"Hepsine toplu privileged" ÖNERİLMEZ** — kontrolü kapatmak güvenlik kararıdır. Meşru olduğu
durum: aynı veri **zaten korunmasız başka bir yoldan** okunuyorsa (ör. sipariş ham `VBAK`'tan).
Bunu iddia etme, **ÖLÇ**; gerekçeyi kodun içine yaz.

✅ **Düzeltmeyi kontrol grubuyla doğrula:** aynı sorguyu klozlu/klozsuz koş — **yetkili** kullanıcıda
sonuç kümesi **değişmemeli** (değişiyorsa regresyon). Bu, kısıtlı test kullanıcısı gerektirmez.

📖 Sınıfın tamamı (yazma yoluna bulaşması, kısmî red, PFCG ölçüm tuzağı `AGR_1251` vs **`AGR_1252`**):
[`lessons-learned.md` PATTERN #32](lessons-learned.md).

> **prior-art: YOK** (ölçüldü 2026-08-14 — `rg "WITH PRIVILEGED ACCESS|CDS_Access_Control"` →
> `playbook/` + `standards/` altında **0 eşleşme**). Ders 2026-08-11'den beri yalnız bir proje
> sınıfının yorum bloğunda + o paketin SESSION_NOTES'unda yaşıyordu ⇒ başka bir pakette aynı
> tuzağa **yeniden düşüldü** (2026-08-14, 5 nokta). Terfi sebebi bu.
> **Enforcement:** doküman + reviewer yargısı (checklist BE-67). **Gate AÇILMADI** — ADR 0019
> moratoryumu şart-4: önce doküman katmanı denenir; "doğrudan erişim + `#CHECK`" statik olarak
> güvenilir biçimde ayırt edilemiyor (dolaylı erişim meşru ve yaygın) ⇒ otomatik kural
> yanlış-pozitif üretirdi.

## ⛔ CDS-DCL-02 — **TERS YÖN**: released halefe geçerken `#CHECK` halef **fail-open** üretebilir (2026-08-14)

> **Güç: MUST (karar kuralı).** Clean Core disiplini *"ham standart tablo yerine released CDS"*
> der (`released_successors.json` · validator WARNING `C-CC-REL-01`). ⚠ **Ham DDIC tablo DCL
> TAŞIMAZ; released halef taşıyabilir.** Yani geçiş, DCL'siz bir okumayı **DCL'li** bir okumaya
> çevirir — CDS-DCL-01'in tuzağını **kendi elinle kurabilirsin.**

**Neden sadece "eksik veri" değil:** okunan veri bir **guard/kontrol** besliyorsa, 0 satır
*"kontrol maddesi yok"* diye okunur ⇒ **fail-OPEN**. Sessiz kırıklık burada bir **güvenlik
kusuruna** dönüşür.

> **Ölçülmüş vaka (2026-08-14):** teslimat yaratmadan önce **partner blok kontrolü** ham `VBAK`'tan
> okuyordu. Halef `I_SalesDocument` `@AccessControl.authorizationCheck: #CHECK` taşıyor (canlı
> okundu) ⇒ geçilseydi dar yetkili kullanıcıda 0 satır → *"blok yok"* → **bloklu partnere teslimat
> oluşurdu.** Halef "daha temiz" olduğu hâlde **geçilmedi**; gerekçe kodun içine yazıldı.

**KARAR KURALI — geçiş önerisi geldiğinde (sıra değişmez):**
① halefin `authorizationCheck` değerini **canlı oku** (annotation; hafızadan/isimden çıkarma)
② okunan veri bir **karar/guard** mı besliyor, yoksa yalnız görüntü mü?
③ 0 satırda davranış **fail-open** mu **fail-closed** mu?
⇒ **`#CHECK` + guard = GEÇME.** Gerekçeyi **koda** yaz — kalıcı WARNING'i susturmak için değil,
gelecekte *"neden hâlâ ham tablo?"* diye soran kişiye (ve bir sonraki reviewer turuna) cevap olsun diye.

⚠ Kural **"geçme"** değil, **"körlemesine geçme"**: halef `#NOT_REQUIRED` ise geçiş güvenlidir ve
tercih edilir. `WITH PRIVILEGED ACCESS`'i "geçiş + kontrolü kapat" diye kullanmak da çare değildir —
o, korunmayan bir okumayı korunuyormuş gibi gösterir (CDS-DCL-01'deki "toplu privileged" yasağı).

📌 **Kapsam şerhi (aynı sınıfın ikinci yarısı):** released disiplini **PROAKTİFTİR** — yazılmakta
olan koda uygulanır. **Mevcut/eski kodda ham tablo kullanımı otomatik bir iş kalemi DEĞİLDİR**;
migrasyon bir **proje politikası** kararıdır (bir projede kullanıcı kararı 2026-08-14: *mevcut
programlar MUAF*). Validator WARNING'i **envanterdir, borç değil** — aksi hâlde her tur aynı liste
"yapılacak" diye yeniden açılır. 📌 Yarım yazılmış kural (yalnız proaktif yarısı), yazılmamış
kuraldan tehlikelidir: var sanılır, eksik yarısı her turda yeniden keşfedilir ve arada yanlış iş üretir.

📖 Sessiz-red sınıfının tamamı: [`lessons-learned.md` PATTERN #32](lessons-learned.md) ·
sözdizimi + uygulanamadığı yerler: **CDS-DCL-01** (yukarıda) · reviewer: checklist **BE-68**.

> **prior-art: BULUNDU ama TERS YÖN YOK** (ölçüldü 2026-08-14): CDS-DCL-01 / PATTERN #32 / BE-67
> sınıfı aynı gün çekirdeğe indi (#137) — hepsi *"`#CHECK` view'dan okuyorsan dikkat"* diyor.
> **Geçiş kararına** dair tek satır yoktu: `playbook/` + `standards/` + `claude/agents/` altında
> released kuralı **koşulsuz** ("released successor öner") yazılıydı. Bu kayıt o boşluğu kapatır.
> **Enforcement:** doküman + reviewer yargısı (**BE-68**). **Gate AÇILMADI** (ADR 0019 şart-4):
> mevcut `check_released_objects` WARNING'i zaten öneriyi üretiyor; eksik olan **kararın kuralı**,
> yeni bir otomatik kontrol değil. Validator çıktısına şerh eklemek **araç değişikliğidir** —
> ayrı öneri olarak açıldı, bu turda YAPILMADI.

## ⛔ CDS-NSDM-01 — classic DDIC view'da `MSEG`/`MKPF` (ve her replacement tablosu) YASAK (2026-08-03)

> **Güç: MUST-NOT.** `@AbapCatalog.sqlViewName`'li **classic (DDIC-based) CDS view** ya da SE11
> view'ın `FROM`/`JOIN`'inde **`DD02L-VIEWREF`'i dolu** bir tablo kullanılamaz. Kullanılırsa view
> **hatasız aktive olur ve DAİMA 0 satır döner.**
>
> **Yerine:** NSDM uyumluluk CDS'i — `mseg` → **`nsdm_e_mseg`** · `mkpf` → **`nsdm_e_mkpf`**
> (alan adları birebir aynı; `sqlViewName`/alan listesi/key/WHERE/UNION **değişmez** → DB view
> yaşar → onu `USING` ile tüketen **AMDP bozulmaz**).
> Emsal: SAP'nin kendi DDIC-based view'ı `C_GdsRcptItemQty` → `select from nsdm_e_mseg`.

**Neden:** S/4'te `MSEG`/`MKPF` **tablo-değiştirme (replacement) objesidir**; veri `MATDOC`'ta,
fiziksel tablo **boş**. Yönlendirme **Open SQL katmanındadır** — `SELECT ... FROM mseg` çalışır.
Classic DDIC view ise **DB seviyesinde** üretilip fiziksel tabloyu okur; onun yönlendirilmesi
view'ın kendi **`DD25L-VIEWREF`**'ine bağlıdır ve bu **yalnız SAP'nin kendi view'larında** dolu
olur — Z view'ında **asla**. **View entity'de bu sorun YOKTUR** (Open SQL yolundan geçer) — ama
view entity **DB view üretmez**, yani AMDP `USING` zinciri varsa çözüm o değildir.

**Etkilenen tablo sınıfı (tam liste sistemden okunur):**
```
SELECT tabname, viewref FROM dd02l WHERE as4local = 'A' AND viewref <> ''
```
MM-IM: `MSEG` `MKPF` · Stok: `MSSA` `MSSL` `MSSQ` `MSCD` `MSFD` `MSID` `MSKU` `MSLB` `MSPR` ·
Değerleme: `MBEW` `EBEW` `OBEW` `QBEW` `VMBEW` (+`*H` tarihsel) · `MARCH` `MARDH` `MCHBH` `MKOLH` …
⚠ `MARA`/`MARC`/`MAKT` replacement **DEĞİLDİR** — onlar classic view'da serbesttir.

**Teşhis (view zaten 0 satır dönüyorsa):**
```
1) SELECT tabname, viewref  FROM dd02l WHERE tabname  = '<TABLO>'    -- replacement mı?
2) SELECT viewname, viewref FROM dd25l WHERE viewname = '<SQL_VIEW>' -- null ⇒ KUSUR BU
3) DD26S ile aynı tabloyu taşıyan TÜM view'lar → her biri COUNT(*) + DD25L-VIEWREF
   → beklenen ayrışma: VIEWREF dolu ⇒ satır var · null ⇒ 0
```
⚠ **Kontrol grubunu kurarken `DD25L-VIEWREF`'i de ölç.** "Standart `CNMSEG` satır döndürüyor,
demek ki classic view'lar MSEG'i görüyor" **yanlış elemedir** — `CNMSEG`'in VIEWREF'i doludur.
Ayırt edici değişken ölçülmezse kontrol grubu hipotezi **tersine çevirir** (bkz.
[`lessons-learned.md`](lessons-learned.md) **PATTERN #21** · #19).

**Neden geç patlar:** ilgili veri kapsamı boşken view zaten 0 döner ve bu **doğru** görünür.
Kusur ilk gerçek veri girildiği gün — genelde kullanıcı testinin ilk saatinde — ortaya çıkar.
Aktivasyon/ATC/`adt_inactive_objects` bu sınıfı **yakalamaz**; tek kanıt **satır saymaktır**.
Ters yönü de unutma: boş view'a `NOT EXISTS`/anti-join yapan sayaç **boşalmaz, ŞİŞER**.

*(applies_to: `s4_private` · `s4_public`. ECC'de bu sınıf yoktur. Gate BİLİNÇLİ olarak
açılmadı — ADR 0019 §4 merdiven ilkesi: önce doküman. Tekrar ederse validator adayı bu kuraldır.)*

---

## ⚡ TEK CDS YARATMA — ÖNCE BUNU OKU (KANONİK, MCP) (2026-06-13)

> **Yeni bir CDS view-entity'yi MCP ile yaratıyorsan, tool sırasını TAHMİN ETME — bu 3 adım:**
>
> 1. **Shell yarat** (raw-REST inline POST, taze CSRF) → `/sap/bc/adt/ddic/ddl/sources`.
>    Desen: `scripts/TempScripts/create_ddls_ve.py` (taze CSRF + `html.escape(src)`). 201 döner
>    ama **source BOŞ kalabilir** (empty-source trap).
> 2. **`mcp__sap-adt__adt_push_source`** (object_type `ddls`, transport) → obje ARTIK VAR →
>    locks + source set + **activate** + active-source doğrular. (Boş-source'u bu düzeltir.)
> 3. **Doğrula:** `adt_get include_source=true` → source DOLU + `version=active`.
>
> **DENENEN BAŞARISIZ (bu sırayı TEKRARLAMA — 2026-06-11 ve 2026-06-13'te 2 kez patinaj):**
>
> | Deneme | Sonuç | Neden |
> |---|---|---|
> | `adt_push_source` ÖNCE (shell yokken) | `[423] not locked` | push_source MEVCUT obje ister |
> | `adt_post_shell` (ddls) | `Unsupported object type: DDLS/DF` | MCP post_shell CDS/DDLS yaratmaz |
> | `create_cds_view.py` (`sap_client.py`) | CSRF "Unknown error" / body ignore | bu sistemde flaky + body'yi yok sayar (§30.1) |
>
> **Batch (çok CDS):** `scripts/populate_cds_views.py` (§30.0). **Mevcut CDS güncelle:** doğrudan `adt_push_source`.

### ⚡ ABSTRACT ENTITY (action param/result — `define [root] abstract entity`, SELECT'SİZ) (2026-06-23 · **rev. 2026-08-22**)

> **📌 2026-08-22 revizyonu — KURAL GÜCÜ DEĞİŞTİ (MAY → MUST) + ölü referans temizlendi.**
> **prior-art: bulundu** — reçetenin kendisi (2026-06-23, bu bölüm) · adım-3'ün *"empty-source trap"* uyarısı · §30.1 *"body'yi yok sayar"* notu (view-entity, komşu obje tipi) · memory `feedback_inline-post-empty-source-trap`.
> ⇒ **Bilgi eksik değildi; adım-2'nin ZORUNLU olduğu yazılı değildi** (*"de olur"* diyordu). Bu revizyon yeni bilgi eklemiyor, **mevcut kuralın gücünü** ölçümle sabitliyor.
> **Ölçümün kapsamı (daraltılmış):** DS4 / S/4 2025, 2026-08-22, **11 obje**. Kontrol grubu: aynı turda adım-1 tek başına **0/11** doldurdu, adım-2 ile **11/11** doldu ve sha256 eşitliği doğrulandı. ⚠ 2026-06-23'teki turun **hangi sistemde** koştuğu kayıtta yok ⇒ *"davranış değişti"* mi *"o sistemde de böyleydi ama fark edilmedi"* mi **AYIRT EDİLEMEDİ**; iddia **bu sisteme** dairdir.

> **Abstract entity ≠ view-entity.** `as select from` / SQL view YOK → SELECT bekleyen araçlar UYGULANMAZ:
>
> | Deneme | Sonuç | Neden |
> |---|---|---|
> | `create_cds_view.py` | "no SELECT" / projection hatası | araç `as select from` bekler; abstract'ta yok |
> | `populate_cds_views.py` | **sprint gate** + TD-spec patlar | batch view-entity üreticisi; abstract için değil |
>
> **ÇALIŞAN (2026-06-23 — nakliye param/result patinajı sonrası):** view-entity 3-adımının abstract uyarlaması —
>
> 1. **POST shell** (taze CSRF, `masterLanguage=TR`, `adtcore:packageRef` + `ddl:sourceMainArtifact`) → `POST /sap/bc/adt/ddic/ddl/sources?corrNr=<TR>`, `Content-Type: application/vnd.sap.adt.ddlSource+xml`.
>    ⛔ **YALNIZ SHELL SAYILIR — inline `<ddl:source>` gömsen bile source'u DOLDURDUĞUNU VARSAYMA.** Ölçüm (**DS4 / S/4 2025, 2026-08-22, 11 obje**): gömülü inline source ile **HTTP 201 CREATED** döndü, aktif source **0 karakter**; ardından toplu aktivasyon `activationExecuted="true"` + `type="E"` **`SDDL_PARSER_MSG 013`** *"The DDIC source code does not contain a valid definition"* ile düştü. ⇒ **`201` tek başına kanıt değildir** (bu evin *"Inline-POST boş-source tuzağı"* dersi; §30.1'in *"body'yi yok sayar"* notuyla aynı davranış).
> 2. ⛔ **FILL — ZORUNLU adım** (bu sistemde opsiyonel DEĞİL): obje başına `adt_push_source` / `SAPClient.push_object(object_type="ddls", source_file=<yerel .cds>)` — kaynağı **DİSKTEN** okut (LLM'de yeniden üretme). `object_types.get_source_url(name,"ddls")` doğru URL'i verir. Sonra aktivasyon: `/sap/bc/adt/activation` (`DDLS/DF` objectReference) ya da push'un kendi aktivasyonu.
> 3. **Doğrula (atlanmaz):** `GET …/source/main?version=active` → gövdede `abstract entity` **GEÇMELİ** + `version=active` + yerel kaynakla **sha256 eşitliği** (CR/son-satırsonu normalize).
>
> ⚠ **Ölü referans (ölçüldü 2026-08-22):** bu maddenin eski hâli `scripts/TempScripts/create_trdoc_abstract.py`'a işaret ediyordu — **o dosya ve `TempScripts/` dizini DEV_CORE'da YOK** (junction üzerinden `ls`/`ls -L`/`find -L` + doğrudan `C:\IX\DEV_CORE\...` + repo-geneli ad araması: dördü de negatif). Deseni script'ten değil, **yukarıdaki 3 adımdan** kur.
>
> **Kural:** "yeni DDLS" görünce TÜRÜNE bak — SELECT var mı? Varsa view-entity 3-adımı; yoksa (param/result/projection-only abstract) bu varyant. Tahminle araç seçme.

## 17. CDS View (DDLS/DF) Yaratma

### 30.0 Production Script

📦 **`scripts/populate_cds_views.py`** — `.cds` source dosyalarından batch CDS view yaratıcı.

```powershell
python scripts/populate_cds_views.py `
  --package ZSD001_CLC `
  --transport <TRANSPORT> `
  --source-dir ERP/SD/ZSD001_CLC/cds `
  --cwd <PROJECT_ROOT>

# Sadece bir CDS:
python scripts/populate_cds_views.py ... --only ZSD001_DDL_CONTAINER_TYPES

# Yeniden yarat:
python scripts/populate_cds_views.py ... --force-recreate
```

Her CDS için bir `.cds` dosyası (DDL source) — script `@EndUserText.label`'dan description çıkarır.

### 30.1 Önemli — 2-Step Pattern Gerek (Tablo Gibi)

Library'nin `create_cds_view()` (`sap_client.py`) **bu sistemde body içine source koyuyor ama SAP body'yi ignore ediyor** (table'daki sorunla aynı, playbook §15).

Doğru akış:
1. **POST shell** `/sap/bc/adt/ddic/ddl/sources` — sadece metadata
2. **LOCK** + **PUT** `/sap/bc/adt/ddic/ddl/sources/{name}/source/main` ile asıl DDL
3. **UNLOCK**
4. **Activate** (`activate_object.py --type cds`)

### 30.2 URL Pattern

```
POST   /sap/bc/adt/ddic/ddl/sources                              ← shell create
GET    /sap/bc/adt/ddic/ddl/sources/{name}/source/main           ← source oku
PUT    /sap/bc/adt/ddic/ddl/sources/{name}/source/main           ← source yaz (lock'lu)
POST   /sap/bc/adt/ddic/ddl/sources/{name}?_action=LOCK          ← lock
POST   /sap/bc/adt/ddic/ddl/sources/{name}?_action=UNLOCK        ← unlock
DELETE /sap/bc/adt/ddic/ddl/sources/{name}                       ← sil
```

ADT type code: `DDLS/DF`

### 30.3 SQL View Adı — 10 Karakter Limit

⚠ **KRİTİK:** `@AbapCatalog.sqlViewName: 'XXX'` değeri **maks 10 karakter** olmalı.

Örnek: `ZSD001_DDL_ORDER_DESTINATION` için SQL view adı `'ZSD001VYDS'` (10 char) — `ZSD001_V_ORDER_DESTINATION` (uzun) olmaz.

Mantıksal kısaltma yöntemi:
| CDS Adı | SQL View Adı |
|---|---|
| ZSD001_DDL_ORDER_DESTINATION | `ZSD001VYDS` |
| ZSD001_DDL_ORDER_SHIP_BAL | `ZSD001DSHB` |
| ZSD001_DDL_ORDER_ORDERES | `ZSD001ORDS` |
| ZSD001_DDL_SHIPPING_TYPES | `ZSD01SHTYP` (prefix 1 char kısa) |

### 30.4 Deprecated Annotation: `preserveKey`

`@AbapCatalog.preserveKey: true` artık SAP S/4'te **deprecated**. Uyarı verir:
```
Annotation 'AbapCatalog.preserveKey' is deprecated and regarded as obsolete.
```

Yeni CDS'lerde kullanma. Eski <LEGACY_SOURCE> source'larından dönüştürürken **kaldır**.

### 30.5 İçerik Annotation'ları (Modern S/4)

```
@AbapCatalog.sqlViewName: 'ZSD001XXXX'   <-- 10 char limit
@AbapCatalog.compiler.compareFilter: true
@AccessControl.authorizationCheck: #NOT_REQUIRED  <-- veya #CHECK
@EndUserText.label: 'Açıklama'
```

### 30.6 Field Adı Doğrulama — DTEL ≠ Field Name

<LEGACY_SOURCE> source'larında bazı field name'ler DTEL adıyla **karıştırılmış olabilir**. Örneğin:
- `T173.versart` ❌ — DTEL adı, field adı değil
- `T173.vsart` ✅ — gerçek field adı (DTEL `versart`)

Sorun çıkarsa SAP GET ile gerçek tablo yapısını çek:
```
GET /sap/bc/adt/ddic/tables/{table}/source/main
```

### 30.7 Aktivasyon

`activate_object.py --type cds` çalışıyor. Modern S/4 uyarıları:
- `preserveKey` deprecated (yukarıda)
- Diğer info-level uyarılar normaldir, aktivasyon başarılı olur

### 30.8 <LEGACY_SOURCE> → TD Namespace Dönüşümü

Eski <LEGACY_SOURCE> CDS'ini içeri taşırken yapılacak değişiklikler:

| <LEGACY_SOURCE> | TD |
|---|---|
| `zsd_007_ddl_X` | `zsd001_ddl_X` |
| `ZSD_007_CV_X` veya `ZSD_007_V_X` (SQL view) | **`ZSD001_V_XXXXX`** (SABİT FORMAT, toplam ≤14 char) |
| `zsd_007_t_X` (Z tablo) | `zsd001_t_X` |
| `zsd_007_e_X` (Z DTEL) | `zsd001_e_X` |
| `zsd_007_d_X` (Z domain) | `zsd001_d_X` |
| `zzitemno` (LIPS append) | `zz1_item_no_dli` |
| `zzitemqty` (LIPS append) | `zz1_item_qty_dli` |
| `zzbooking` (LIKP append) | `zz1_booking_number_dlh` |
| `zzcontainer` (LIKP append) | `zz1_container_number_dlh` |
| `@AbapCatalog.preserveKey` | **KALDIR** (deprecated) |

**⚠️ SQL View Adı KURALI (Sprint 3'te ihlal edildi):**
- Format **`ZSD001_V_XXXXX`** sabittir (8 char prefix + ≤5 char suffix = ≤14 char total)
- ❌ Eski <LEGACY_SOURCE> prefix korunamaz: `ZSD_007_CV_CONCD` YANLIŞ
- ❌ Kısaltılmış format kullanılamaz: `ZSD01CONCD` YANLIŞ (eski stil)
- ✅ Doğru: `ZSD001_V_CONCD`, `ZSD001_V_VOYDS`, `ZSD001_V_ORDIT`

Otomatik dönüştürücü `TempScripts/_convert_cds_sources.py`:
- **Yanlış:** Manuel `sqlview_map = {'ZSD_007_CV_X': 'ZSD01X', ...}` — entry atlanırsa <LEGACY_SOURCE> prefix kalır
- **Doğru:** Regex: `re.sub(r"'ZSD_007_(?:CV|V)_(\w+)'", r"'ZSD001_V_\1'", src)`

### 30.9 TD Namespace WHITELIST — Pre-flight Validation (POZİTİF KURAL)

**Tek doğru format vardır.** Whitelist'te olmayan her şey YASAK. Sprint 3'te ve Sprint 4'te (SHIPPING_TYPES vakası 2026-05-13) bu kuralı negative ifade ettiğim için tekrar hata oldu — şimdi pozitif whitelist:

#### 3 Katmanlı Whitelist Kuralı

| # | Konu | TEK GEÇERLİ FORMAT | Regex (Python) |
|---|---|---|---|
| 1 | sqlViewName annotation | `'ZSD001_V_<1-5 büyük harf/rakam>'` (≤14 char total) | `^ZSD001_V_[A-Z0-9]{1,5}$` |
| 2 | `define view <name>` | `zsd001_ddl_<x>` | `^zsd001_ddl_[a-z0-9_]+$` |
| 3 | Source body referansları | Sadece `zsd001_*` (CDS/tablo/DTEL/domain) | (negative: hiç `zsd_007_*` veya `'ZSD01XXXX'` yok) |

**ÖRNEKLER:**

✅ **DOĞRU CDS başlığı:**
```cds
@AbapCatalog.sqlViewName: 'ZSD001_V_CONCD'
@AbapCatalog.compiler.compareFilter: true
@AccessControl.authorizationCheck: #NOT_REQUIRED
@EndUserText.label: 'Konteyner müşteri detay'
define view zsd001_ddl_container_customer
  as select from likp
    left outer join zsd001_ddl_shipping_types as ShipType on ...   -- ✅ Z-CDS ref TD namespace
```

❌ **YASAK örnekler (script HEMEN FAIL eder):**
```cds
@AbapCatalog.sqlViewName: 'ZSD_007_CV_CONCD'    -- Katman 1: <LEGACY_SOURCE> prefix
@AbapCatalog.sqlViewName: 'ZSD01CONCD'          -- Katman 1: eski kısaltma
@AbapCatalog.sqlViewName: 'ZSD001_V_TOOLONG'    -- Katman 1: 14+ char
define view zsd_007_ddl_x                       -- Katman 2: eski namespace
... left outer join zsd_007_ddl_y               -- Katman 3: source body'de orphan ref
... left outer join 'ZSD01ORDDS'                -- Katman 3: eski stil literal
```

#### Pre-flight Check (kod düzeyi, otomatik, bypass edilemez)

`scripts/populate_cds_views.py` → `validate_sql_view_names()` fonksiyonu **dosya okuma + SAP bağlantısı + POST/PUT aktivasyon işleminden ÖNCE** çağrılır. Tek bir ihlal varsa script `exit 1` ile çıkar, hiçbir SAP isteği yapılmaz.

```python
SQL_VIEW_PATTERN  = re.compile(r"^ZSD001_V_[A-Z0-9]{1,5}$")
VIEW_NAME_PATTERN = re.compile(r"^zsd001_ddl_[a-z0-9_]+$")
SQL_VIEW_MAX_LEN  = 14

BANNED_SOURCE_PATTERNS = [
    (re.compile(r"\bzsd_007_\w+", re.IGNORECASE),
     "<LEGACY_SOURCE> namespace referansı"),
    (re.compile(r"'ZSD_007_(?:CV|V)_\w+'"),
     "Eski <LEGACY_SOURCE> sqlViewName literal'i"),
    (re.compile(r"'ZSD\d{2}[A-Z]{4,8}'"),
     "Eski kısaltılmış sqlViewName literal'i"),
]

def validate_sql_view_names(cds_files):
    """3 katman whitelist: sqlViewName + view name + source body."""
    errors = []
    for f in cds_files:
        source = f.read_text(encoding='utf-8')
        # Katman 1
        m = re.search(r"@AbapCatalog\.sqlViewName\s*:\s*'([^']+)'", source)
        if not m or not SQL_VIEW_PATTERN.match(m.group(1)):
            errors.append(f"{f.name}: sqlViewName whitelist ihlali")
        # Katman 2
        vm = re.search(r"\bdefine\s+view\s+(\S+)", source, re.IGNORECASE)
        if not vm or not VIEW_NAME_PATTERN.match(vm.group(1).lower()):
            errors.append(f"{f.name}: view name whitelist ihlali")
        # Katman 3
        for pat, msg in BANNED_SOURCE_PATTERNS:
            for hit in pat.finditer(source):
                line = source[:hit.start()].count('\n') + 1
                errors.append(f"{f.name}:{line}: yasak '{hit.group(0)}' — {msg}")
    return errors
```

#### Manual Kontrol Komutları (her CDS batch'inden önce çalıştır)

```powershell
# 1. sqlViewName whitelist'te DEĞİL olan dosyalar (BOŞ çıkmalı)
grep -EL "^@AbapCatalog\.sqlViewName:\s*'ZSD001_V_[A-Z0-9]{1,5}'" ERP/SD/ZSD001_CLC/cds/*.cds

# 2. view name whitelist'te DEĞİL olan dosyalar (BOŞ çıkmalı)
grep -EL "^define view zsd001_ddl_" ERP/SD/ZSD001_CLC/cds/*.cds

# 3. Source body'de YASAK referans (BOŞ çıkmalı)
grep -nE "(zsd_007_|'ZSD_007_(CV|V)_|'ZSD[0-9]{2}[A-Z]{4,8}')" ERP/SD/ZSD001_CLC/cds/*.cds
```

#### Namespace Converter (gelecek modüller için — manuel dictionary YASAK)

```python
# 1. sqlViewName
src = re.sub(
    r"@AbapCatalog\.sqlViewName\s*:\s*'ZSD_007_(?:CV|V)_(\w+)'",
    lambda m: f"@AbapCatalog.sqlViewName: 'ZSD001_V_{m.group(1)[:5]}'",
    src
)
# 2. view name
src = re.sub(r'\bzsd_007_ddl_', 'zsd001_ddl_', src, flags=re.IGNORECASE)
# 3. Tablo/DTEL/Domain
src = re.sub(r'\bzsd_007_t_', 'zsd001_t_', src, flags=re.IGNORECASE)
src = re.sub(r'\bzsd_007_e_', 'zsd001_e_', src, flags=re.IGNORECASE)
src = re.sub(r'\bzsd_007_d_', 'zsd001_d_', src, flags=re.IGNORECASE)
```

> **⚠️ TADIR Cleanup Hatırlatma:** Bir DDL source SAP'de bir kez `ZSD01XXXX` veya `ZSD_007_*` sqlViewName ile aktive edildiyse, source dosyada `ZSD001_V_X` yazsanız bile **rename broken**. Çözüm: transport release et (TADIR clean) → yeniden aktive et. DELETE workbench-level yetmez. Sprint 3-4'te toplam 3+ kez yaşandı.

### 30.10 DB SQL View Orphan Cleanup (Sprint 4 Keşfi — 2026-05-13)

**🎯 Kritik Keşif:** DDL source workbench-level DELETE ≠ DB DDIC catalog SQL view drop. Transport release + workbench DELETE sonrası bile **DB DDIC catalog'ta SQL view orphan kalır**. Bu orphan, aynı DDL source'u farklı sqlViewName ile aktive etmeyi engeller ("rename broken").

#### Pattern (Sprint 3'ten kalma 9 vaka, hepsi Sprint 4'te keşfedildi)

Sprint 3'te yaratılan DDL source'lar 2 farklı sqlViewName stiliyle aktive edilmişti:

| Source dosyada beklenen | Sprint 3'te DB'ye yazılan |
|---|---|
| `ZSD001_V_CONCD` | `ZSD_007_CV_CONCD` (<LEGACY_SOURCE> prefix korundu) |
| `ZSD001_V_VOYDS` | `ZSD001VYDS` (kısaltılmış stil) |
| `ZSD001_V_SHTYP` | `ZSD01SHTYP` (kısaltılmış stil) |
| ... | ... |

Source dosyalar düzeltilse de DB DDIC catalog'ta eski sqlView'lar orphan kaldı. Workbench-level GET/DELETE bunları silemedi — DB-level SE14 cleanup şart.

#### Tespit Yöntemi

`TempScripts/_probe_orphans.py` her CDS için POST shell + PUT + ACTIVATE dener, hata mesajındaki `SQL view (\w+) cannot be renamed` pattern'ından orphan SQL view adını çıkarır. Çıktı: orphan listesi → user'a verilir.

#### Cleanup (SAP-side, manual — ADT API'den yapılamaz)

**Yöntem 1 — SE14 (Database Utility):**
```
SE14 → Object Type: VIEW → İsim: <ORPHAN_VIEW>
  → Edit → Object → "Delete from database" → transport'a koy
```

**Yöntem 2 — SE38 / RSDDDDCDELOLD:**
Orphan DDIC view toplu temizleyici raporu. Liste mode ile çalıştır, seçim yap.

**Yöntem 3 — Direkt SQL (sıra dışı):**
```sql
-- SE16N → DD02L tablosunda VIEWNAME = <ORPHAN> kayıtları görüntüle
-- Kayıt varsa SE11/SE14 cleanup gerek
```

#### Tam Temizlik Sırası

```
1. Probe (script) → orphan listesi
2. User: SE14'ten her orphan'ı transport'a koyup sil
3. User: transport release et (<TRANSPORT>)
4. Script: POST shell + PUT source + Activate → temiz aktivasyon
5. Doğrulama: SELECT * FROM <YENİ_SQL_VIEW>
```

#### Önleme (Gelecek Modüller için)

- ✅ İlk yaratımda **doğru sqlViewName** kullan (whitelist-only)
- ✅ Pre-flight check (§17.9) atlanırsa script `exit 1`
- ❌ "Sonra düzeltirim" diyerek geçici/yanlış sqlViewName ile aktive **ASLA ETME** — temizliği saatler sürer

> **⚠️ Operasyonel Maliyet:** Sprint 4'te 9 orphan tespit edildi, hepsinin DB-level cleanup'ı user-side iş + transport release. **2-3 saatlik geriye dönük temizlik** + **+1 saat yeniden aktivasyon**. Pre-flight check kuralı bunu önler.



---

## CDS Yaratma Tuzakları — `create_cds_view` + yeni view (2026-06-11)

Yeni CDS yaratırken yaşanan 3 tuzak (ZSD001_I/C_MAT_LOOKUP). **Kanonik akış: `create_cds_view` (shell) → `push_object` (gerçek source + activate).**

### T1 — `create_cds_view` source'u XML'e gömerken escape etmiyordu → `<>`/`<`/`&` "Unknown error"
- **Belirti:** `create_cds_view` "Request failed after 3 retries: Unknown error" (retry-wrapper gerçek HTTP hatasını gizler). Object yaratılmaz → sonraki `push_object` `[423] not locked`.
- **Kök neden:** create POST gövdesi `<ddl:source>{cds_source}</ddl:source>` — source RAW gömülüyordu. `case when x <> 0` / `<` / `&` → XML bozulur → SAP reddeder.
- **Neden bazı view'lar çalıştı:** içinde `<>` olmayan source'lar (ör. basit agregasyon) escape gerektirmedi.
- **FIX (uygulandı):** `sap_adt_lib.create_cds_view` artık `html.escape(cds_source, quote=False)` ile gömüyor. Tekrar etmez.
- **Workaround (fix yoksa):** shell'i `<>`-içermeyen minimal/escaped source ile yarat, sonra `push_object` ile gerçek source'u yükle (source endpoint text/plain → `<>` sorunsuz).

### T2 — Opaque hatada YÖNTEM DEĞİŞTİRME, önce GERÇEK hatayı yakala
- Bu vakada create_cds_view → minimal shell → MCP post_shell diye dolanıldı (zaman kaybı). Doğrusu: ham `session.post(...)` ile `response.status_code + response.text` yazdırıp gerçek hatayı görmek (XML break anında ortaya çıktı). Bkz. memory `feedback_playbook-once-oku` (tahminle deneme yok).

### T3 — Read-only consumption = `as select from`, `as projection on` DEĞİL
- `define view entity ... as projection on <I_view>` → "**Transactional Projection View must be part of a business object**" (projection = RAP transactional → BDEF/BO ister).
- Salt-okunur OData lookup (BO yok) için **`as select from <I_view>`** (düz view) kullan. `@Semantics` annotation'ları consumption'da tekrar bildir.
- Ayrıca: `define root view entity ... as projection on <non-root>` → "ROOT keyword not valid" (projection ROOT olamaz interface root değilse).

### T4 — UNION view-entity 3 KURALI (2026-06-19, ZSD001_I_BATCH_STOCK EWM/MM union) — peşinen uygula, aksi her biri AYRI aktivasyon turu
Bir `define view entity ... union all ...` yazarken SAP 3 kuralı tek tek dayatır (4 tur ping-pong'a mal oldu). **HEPSİNİ baştan uygula:**
- **(a) WHERE'de `NOT EXISTS`/`EXISTS` subquery YASAK** → `Unexpected keyword "exists"`. Kanonik anti-join: **LEFT OUTER JOIN + `WHERE <join>.key IS NULL`** (eşleşmeyenleri tut). (Eski `DEFINE VIEW`'de EXISTS vardı; view-entity'de yok.)
- **(b) Element-level `@Semantics.*` (quantity/amount vb.) YALNIZ 1. (ilk) SELECT dalında** → `Annotations are not allowed in this branch`. Sonuç-element annotation'ı 1. daldan miras alınır; 2.+ dallarda TEKRARLAMA.
- **(c) Header'da `@Metadata.ignorePropagatedAnnotations: true` ZORUNLU** (propagate-edilebilir @Semantics.quantity varsa) → `Annotation Metadata.ignorePropagatedAnnotations is required`.
- Ayrıca: iki dal **field-sayısı/sıra/tip BİREBİR** (literal cast'lerle hizala). bug-gate (read-only) bunları YAKALAYAMAZ (syntax yalnız push+activate'te çıkar) → gateway aktivasyonu güvenlik ağı.

### T5 — conv-exit'li alan OData expose → publish FAIL → `cast()` ile exit düş (2026-06-19)
- **Belirti:** CDS aktive olur AMA `adt_publish_service`/`$metadata` FAIL: `Do not use conversion exit <EXIT> for property <FIELD>`. SADL/OData V2 property'de conversion-exit'i reddeder.
- **Sık alanlar:** `/scwm/de_huident` (HUID — HU no), kur/EXCRT/birim exit'li DTEL'ler.
- **FIX:** alanı `cast( <field> as abap.char( <len> ) )` (veya uygun plain tip) ile expose et → exit düşer, değer korunur. (HUID = char 20.) UNION'da İKİ dalda da tip-hizalı cast.
- **Önleme:** EWM/HU/kur alanı OData picker/UI'a expose edilecekse, CDS'te baştan plain-cast et. Ref: `ui-backend-rap.md` conv-exit notu.

### T6 — JOIN'de kullanılan alanın RENAME/SİL'i → aktivasyon deadlock → **transitional 3-adım swap** (2026-06-20, ZSD001 CONTAINER_SHIPMENT→booking-item)
- **Belirti:** Bir view'da (A) bir alanı (X) silince/yeniden-adlandırınca SAP bloklar: *"Field <SQLVIEW>-X is still being used in join of <CONSUMER_VIEW>"*. Tüketici (B) view A'nın X alanını JOIN şartında kullanıyor. Atomik co-activation (`adt_activate` + `also`, her iki sıra) da **"column <Y> is unknown"** ile FAIL — SAP inactive↔inactive arası JOIN-alanı rename'ini tek worklist'te çözmez.
- **FIX (kanonik non-destructive alan-rename deseni):** 3 adım, her biri **tek-obje aktive**:
  1. A'ya YENİ alanı (Y) **EKLE** (eski X'i KORUYARAK) → A tek-aktive (X hâlâ var, tüketici kırılmaz).
  2. Tüketici B'nin JOIN'ini **Y'ye çevir** → B aktive.
  3. A'dan eski X'i **SİL** (nihai hedef) → A aktive (artık kimse X'i join'de kullanmıyor).
- **Not:** Yeni/eski alan 1:1 eşlenikse (ör. container_no ↔ booking_item her ikisi de aynı kayıt granülaritesi) group-by/agregasyon sonucu (ShipmentCount vb.) değişmez. Çıktı kolonları aynı kalırsa tüketici RAP/servis ETKİLENMEZ ($metadata aynı → republish gerekmez, yine de doğrula).
- **Önleme:** Bir CDS alanını tüketici JOIN'i varken doğrudan rename/sil ETME; önce ekle→tüket-çevir→sil.

### T7 — `CASE WHEN` sol-taraf aritmetiği DIŞ PARANTEZ ile sarmalanMAZ → aktivasyon `Unexpected word ')'` (2026-06-21, ZSD001_I_SHIP_POOL SeStatus)
- **Belirti:** Computed alan `cast( case when ( <aritmetik> ) <= 0 then 'C' else 'A' end as abap.char(1) )` → `adt_syntax_check` **valid:true** dönse de **aktivasyon FAIL**: `Unexpected word ')'` (konum = kapanan dış paren).
- **Kök neden:** CDS `CASE WHEN`'de karşılaştırmanın SOL tarafındaki aritmetik ifadeyi **parantezle gruplamayı kabul etmiyor**. `when ( a - b ) <= 0` → red; `when a - b <= 0` → OK.
- **FIX:** dış parantezleri kaldır, aritmetiği parantezsiz yaz (aynı dosyadaki ham aritmetik alanın — ör. OpenQty `cast(qty) - coalesce(...)` — deseniyle birebir). İç cast'ler (semantic-strip) kalır, yalnız gruplama-pareni gider.
- **DERS (kritik):** `adt_syntax_check` bu hatayı YAKALAMAZ (pre-push/canlı kaynağı okur, yeni computed alan henüz orada yok) → **aktivasyon = tek güvenilir syntax gate** (bug-gate read-only de yakalayamaz; gateway aktivasyonu güvenlik ağı). "syntax_check geçti" ≠ "aktive olur". Bkz. memory `feedback_abaplint-parser-error-gercek-olabilir` ikizi.

### T8 — JOIN ON karşılaştırmasında `cast()`/FUNCTION güvenilmez (COMP_LEFT yasak) → PRE-CAST KÖPRÜ-VIEW kullan (2026-06-24, ZSD001_I_NAVLUN_REPORT vfkp⨝vtts numc-mismatch)
- **Belirti:** İki farklı uzunluktaki numerik key'i join etmek için ON şartında cast kullanılınca aktivasyon FAIL: `Expression type FUNCTION not allowed in expression context COMPARISON, clause type COMP_LEFT`. Örn (RED): `and cast(Stage.tsnum as abap.numc(6)) = Cost.repos`.
- **Kök neden:** CDS JOIN ON karşılaştırmasında cast/fonksiyon ifadesi GÜVENİLMEZ; SOL operandda kesin YASAK (`COMP_LEFT`), sağ operandda da garanti DEĞİL (release-bağımlı). Bu yüzden inline cast'e (flip dahil) GÜVENME.
- **ÇALIŞAN (KANONİK) = PRE-CAST KÖPRÜ-VIEW + LPAD (cast TEK BAŞINA YETMEZ):** alt view vtts'i 6-haneye getirip expose etsin → ana view DÜZ join'lesin (`Cost.repos = Stage.TsnumC6`, `Cost.rebel = Stage.Tknum`). Cast tüketici ON'undan kalkar, COMP_LEFT yasağı düşer. Dosya: `ERP/SD/ZSD001_CLC/cds/ZSD001_I_NAVREP_STAGE.cds`.
- **⚠️ İKİNCİ TUZAK (2026-06-24, aynı obje, 2. round-trip):** köprü-view İÇİNDE bile `cast(tsnum as abap.numc(6))` AKTİVASYONDA FAIL: `CAST NUMC ... lengths must match`. CDS **numc(N)→numc(M) (N≠M) cast'ine izin VERMEZ** (projeksiyonda da). DOĞRU FORM = önce `lpad` ile 6-char string yap, SONRA **eşit-uzunluk** cast: `cast( lpad( Stage.tsnum, 6, '0' ) as abap.numc(6) ) as TsnumC6` (char(6)→numc(6), uzunluk eşit → geçer).
- **KANIT (<LEGACY_SOURCE> — yanlış anlaşılmıştı):** orijinal `zsd_024_v_nklklm` bir **klasik SE11 DDIC view** (CDS değil, ADT 404); `tsnum6`'yı SE11 conversion ile üretiyor — CDS `cast()` deseni DEĞİL. Yani köprü FİKRİ doğru ama CDS cast tekniği <LEGACY_SOURCE>'dan kopyalanamaz; lpad+eşit-uzunluk-cast bizim CDS-valid çözümümüz.
- **NUMC uzunluk değişimi:** doğrudan numc→numc cast (4→6) YASAK; `lpad(...,6,'0')` → eşit-uzunluk cast ile çöz. Uzun key'i kısaltma (veri kaybı) zaten YASAK.
- **DENENEN ZAYIF (flip):** cast'i sağ operanda almak (`Cost.repos = cast(...)`) teorik olarak COMP_LEFT'i atlatabilir ama `adt_syntax_check` yalnız SERVER'daki inactive/canlı kaynağı okur (inline-source kabul ETMEZ) → push'tan önce flip'in derlendiği DOĞRULANAMAZ. Doğrulanamayan flip yerine kanıtlı köprü-view tercih edilir (gateway round-trip garantisi).
- **FS:** köprü-view "gerekmez" diyen FS'e as-built notu düş (derleyici zorunlu kıldı = meşru teknik gereklilik).

### T9 — `string_agg` bu sistemin ABAP CDS view-entity compiler'ında DESTEKLENMİYOR → 1:N liste için native `count` + `max`-temsilci (2026-06-24, ZSD001_I_SE_BOOKING/PLATE/DELIVERY_AGG)
- **Belirti:** Agregat view'de `string_agg(col, ', ')` ile 1:N değerleri virgüllü listeye toplama → AKTİVASYON FAIL: `Activation was cancelled. Column <col> is not contained in the GROUP BY list`. Compiler `string_agg`'i aggregate olarak TANIMIYOR → col'u non-aggregated sayıp GROUP BY hatası veriyor.
- **Kök neden:** ABAP CDS view-entity'de string aggregation YOK (MAX/MIN/SUM/AVG/COUNT var, string_agg yok). S4CORE sürüm-numarasına bakıp "destekli" varsaymak (çıkarım) **canlı aktivasyonla çürür** — capability iddiası = CANLI TEST, versiyon-çıkarımı DEĞİL. Codebase'de proven precedent yoksa şüpheci ol.
- **ÇALIŞAN (KANONİK):** 1:N özet için native `count(*)`/`count(distinct ...)` (adet) + `max(...)` (temsilci/son tek değer). [0..1] grain GROUP BY ile korunur. Tam virgüllü liste GEREKİYORSA AMDP/table-function (CDS native değil). Kanıt: FREIGHT_COST max, ORDERED_QTY count/sum.
- **Karar deseni:** "Booking No(lar)/Teslimat No(lar)" gibi liste-istekleri salt-okunur özet raporda **adet + temsilci(max)**'e indirilebilir (per-belge detay drill-down/kardeş raporda); FS'e as-built notu, sessizce düşürme.
- **Reviewer dersi:** bug-checklist-BE → "CDS capability iddiası (string_agg vb.) versiyon-çıkarımıyla DEĞİL, codebase proven-precedent veya canlı aktivasyonla doğrulanır" satırı.

### T10 — Sanal element (virtual element) + SADL calc-exit: JOIN'lenemeyen kaynaktan (STXL metni vb.) hesaplanmış kolon (2026-06-29, ZSD001_C_SE_REPORT 3 sipariş notu; ZCL_SD001_SEREP_TEXTS)
> **Ne zaman:** CDS'e DB-join ile gelemeyen bir değer (uzun metin/STXL READ_TEXT, hesap, dış-kaynak) **görüntü kolonu** olarak gerekiyor. Çözüm = `@ObjectModel.virtualElement` + `IF_SADL_EXIT_CALC_ELEMENT_READ` ABAP exit. **İlk-kez bu sistemde**; 4 tur patinaj yaşandı, hepsi aşağıdaki tuzaklardı.

**KANONİK reçete (ZSD001_C_SE_REPORT + ZCL_SD001_SEREP_TEXTS):**
- CDS (`as select from` consumption): `@ObjectModel.virtualElement: true` + `@ObjectModel.virtualElementCalculatedBy: 'ABAP:ZCL_...'` + **`cast( '' as abap.char( N ) )`** (flat-tip ZORUNLU; aşağı T10-a). Exit'in ihtiyacı olan kaynak alan (ör. OrderNo) view'da bulunmalı.
- Exit class `IF_SADL_EXIT_CALC_ELEMENT_READ`: `get_calculation_info` (istenen orig-element'leri bildirir) + `calculate` (değerleri doldurur).

**T10-a — `abap.string` CAST'ta GEÇERSİZ:** select-from view'da sanal alan CAST ile tiplenir; CDS CAST **yalnız flat tip** alır → `cast('' as abap.string)` aktive OLMAZ. Üst sınır **`abap.char(1333)`** (= Edm.String MaxLength 1333). Gerçek unbounded gerekiyorsa ayrı mimari (projection view / function-import) — başlık-notu için aşırı. (`virtual <ad> : abap.string` düz-tip yalnız `as projection on`/abstract entity'de.)

**T10-b — `get_calculation_info` orig-element adı CASE-SENSITIVE UPPERCASE:** `CL_SADL_EXIT_HANDLER=>_check_orig_element` adı `sadl_entity-elements`'te case-sensitive arar; SADL element adları UPPERCASE. `et_requested_orig_elements`'a **`'ORDERNO'`** (camelCase `'OrderNo'` DEĞİL) → aksi `CX_SADL_EXIT_WRONG_ELMENT` → **RAISE_SHORTDUMP** (OData 500, calculate'ten ÖNCE). Çalışan std örnek: `CL_SDBIL_PBD_VIRTUAL_ELEMENT` (`WHEN 'WBSDESCRIPTION'. INSERT |WBSELEMENTEXTERNALID|`). `calculate` 1:1 index (it_original_data↔ct_calculated_data, `sy-tabix`); tablo-ifadesi `itab[...]` DEĞİL `READ TABLE` (eşleşme yoksa CX_SY_ITAB_LINE_NOT_FOUND dump).

**T10-c — Metin OKUMASI: READ_TEXT yerine PROVEN okumayı yeniden kullan (dil + tdname tuzağı):** STXL metni için `READ_TEXT` çift-tuzak: (1) **tdname yazıcıyla BİREBİR** olmalı — yazıcı ham `vbeln` yazdıysa `ALPHA_INPUT`'u CHAR70 tdname'e koyma (70-haneye zero-pad → eşleşmez → boş); (2) **dil** — `READ_TEXT language=sy-langu` OData runtime'da TR olmayabilir (metin 'T'de kayıtlı) → boş. **ÇÖZÜM:** zaten çalışan okumayı reuse et — burada `ZSD001_CL_SO_MANAGER->get_order_texts` (RAP `READ ENTITIES ... BY \_Text`, dil-bağımsız, FIT_SE ekranıyla AYNI). Cross-paket ref kabul (UI da aynı servisi kullanıyor). **DERS:** "bu değer başka ekranda zaten çalışıyorsa, o okumayı kopyala — sıfırdan READ_TEXT kovalama."

**T10-d — CANLI DOĞRULAMA ŞART (statik bug-gate runtime'ı görmez):** sanal element exit'i statik review/syntax/ATC'den GEÇER ama runtime'da dump/boş döndürebilir. Doğrulama tekniği (browser'sız):
- OData curl (.conn_adt kimliği, şifre echo'suz): `curl -s -k -u "$U:$P" ".../<SRVB>/<Entity>?$select=...&$format=json&sap-client=100"` → HTTP 500 = dump; boş alan = okuma bug'ı.
- Dump KÖK-NEDEN: ADT runtime-dumps feed → `curl ... -H "Accept: application/atom+xml;type=feed" ".../sap/bc/adt/runtime/dumps?sap-client=100"` → exception adı (CX_SADL_EXIT_WRONG_ELMENT vb.) + bizim-class satırı. **Tahmin etme, dump'a bak.**
- STXH/STXL gerçek key teyidi: gateway `adt_classrun` read-only probe (`SELECT ... FROM stxh WHERE tdobject=.. AND tdname LIKE ..`).
**Reviewer dersi:** bug-checklist-BE → "sanal element/SADL calc-exit = statik gate YETMEZ → canlı OData curl + (boşsa) dump-feed/STXH probe ile doğrula".

### T11 — base ELEMENT rename + consumption o alanı seçiyor → karşılıklı bağımlılık kilidi → **atomik co-activation** `adt_activate(base, also=[consumption])` (2026-07-01, ZSD001 çıkış→müşteri ülkesi rename)
> **Ne zaman:** base view'da bir alan RENAME edilir (ör. `klm_cikis_ulkesi`→`klm_musteri_ulkesi`) ve consumption view o alanı `as select from` ile tüketir. Tek-obje aktivasyon **iki yönlü kilitlenir** (T6 akrabası — ama T6 JOIN-alanı sil/rename için transitional 3-adım; bu, base↔consumption select bağımlılığı).
- **Belirti:** base tek-başına aktive → `Field ZSD001_V_INVOICE-KLM_CIKIS_ULKESI is still being used in view ZSD001_C_INVOICE` (aktif consumption hâlâ eski adı kullanıyor). Consumption tek-başına → `column klm_musteri_ulkesi is unknown` (aktif base hâlâ eski). Deadlock.
- **ÇÖZÜM:** her iki DÜZELTİLMİŞ kaynağı **inaktif upload** et (push, activate etme), sonra **tek POST'ta** `adt_activate(base, also=[consumption])` → atomik co-activation (`activationExecuted=true`, refs=her ikisi). Yeni-yeni birlikte aktive olur, ara-durum kilidi oluşmaz.
- **🔁 TEKRAR (2026-07-30) — pattern belgeliydi, KİMSE OKUMADI.** Aynı sınıf ikinci kez yaşandı: bir base view'da `islem`→`islem_turu` rename edildi, consumption o alanı seçiyordu. **Belirtiler bu maddedekiyle birebir aynı çıktı** (`... is still being used as a view field in view ...` / `The column ... is unknown`) ve çözüm de aynıydı. **Bedeli:** iki başarısız aktivasyon turu. **Asıl bulgu teknik değil süreçsel:** push paketini hazırlayan ajan, onaylayan lider ve icra eden gateway — **üçü de obje-tipi playbook'unu (bu dosyayı) taramadan** "önce base, sonra consumption" planı kurdu; gateway çözümü **yeniden keşfetti**. Kayıp kurtarılabilir ve gürültülüydü (aktivasyon bağırır) → runtime gate'e ait DEĞİL, **disipline** ait: *push/aktivasyon planı yazmadan önce obje-tipi playbook'unun tuzak listesi taranır* — özellikle **alan RENAME/SİL** içeren her değişiklikte (T6 + T11 birlikte). Kural: **kırıcı alan yeniden-adlandırması = tüm tüketicilerle ATOMİK aktivasyon**, tıpkı BDEF+behavior gibi.
- **T11-a — `content_mismatch` false-alarm:** co-activation sonrası tool `content_mismatch=true` dönebilir — stale `_LAST_PUSHED` baseline aktifi ESKİ kaynakla kıyaslar. Körü körüne "başarısız" sayma → **`adt_get version=active` ile bağımsız teyit** (kaynakta yeni join/alan var mı). Araç-readback ≠ canlı gerçek (feedback_arac-basarisizligini-zararsiz-sayma tersi de geçerli: false-NEGATIF).

### T12 — `concat` **arg1'in SONDAKİ BOŞLUKLARINI SİLER** → ayıraçlı birleştirme sessizce bozulur; çözüm `concat_with_space` (2026-07-28, ZSD001 birleşik kimlik kolonu)
> **Ne zaman:** iki kolonu görünür bir ayıraçla birleştiriyorsun — `"KNT1010110101 · 34RRR334"` gibi. Sezgisel yazım **yanlış çıktı üretir ve hiçbir hata vermez.**

- **Belirti (ölçüldü, canlı):**
  ```
  concat( col_a, concat( ' · ', col_b ) )   ->  "KNT1010110101 ·34RRR334"   ← ayıraçtan SONRA boşluk YOK
  ```
  Aktivasyon geçer, syntax check geçer, ATC geçer. Yalnız **çıktıya bakarsan** görürsün.
- **Kök neden:** CDS/OpenSQL `concat` **birinci argümanın sondaki boşluklarını kırpar**. `' · '` literali arg1 konumuna düştüğü an `' ·'` olur. İç içe yazımda literal **iç** `concat`'in arg1'idir → boşluk orada ölür.
- **⛔ ÇALIŞMAYAN "düzeltme":** literali dışa almak da **kurtarmaz** — `concat( concat( col_a, ' · ' ), col_b )` bu kez **dış** `concat` arg1'in (yani birleşimin) sondaki boşluğunu siler → aynı sonuç. *Ölçmeden "böyle olur" deme; bu varyant bug-gate'te önerildi, backend ölçümüyle çürütüldü.*
- **✅ ÇALIŞAN (KANONİK):**
  ```
  concat_with_space( concat_with_space( col_a, '·', 1 ), col_b, 1 )   ->  "KNT1010110101 · 34RRR334"
  ```
  Üçüncü argüman eklenen boşluk sayısıdır; ayıracı **boşluksuz** ver, boşlukları fonksiyon koysun.
- **🆕 PRECEDENT KAYDI — `concat_with_space` VIEW ENTITY'de ÇALIŞIYOR (2026-07-28 aktivasyon + readback ile kanıtlandı).** O tarihe kadar codebase'deki tüm kullanımları **klasik DDL view**'daydı; view entity precedent'i YOKTU ve bu, BE-27 gereği bir risk olarak işaretlenmişti. **Artık kanıtlı — bir daha riskli sayma.**
  ⚠ Yan gözlem: **Open SQL freestyle ucu** `CAST( concat_with_space( col, '<literal>', 1 ) AS CHAR(n) )` çağrısını **400** ile reddediyor. Bu bir **endpoint** sınırıdır, **dil sınırı DEĞİL** — CDS derleyicisi kabul etti. Data-preview'ın reddini "CDS bunu desteklemiyor" diye okuma (T13'ün akrabası).
- **Neden sessiz:** birleşim dalı çoğu zaman **hiç tetiklenmez** (her iki kolonun da dolu olduğu satır yoksa). Vakada defekt aylardır canlıydı ve **hiç görünmemişti**; ancak veri koşulu oluştuğunda ortaya çıkacaktı. ⇒ Bir ifadeyi TAŞIRKEN kopyalama — **canlı koş ve çıktısını gör**.
- **Reviewer dersi:** bug-checklist-BE → "ayıraçlı `concat` birleştirmesi: literal ayıracın boşlukları **kırpılır** → `concat_with_space` kullan; taşınan ifade **çıktısıyla** doğrulanır".

### T13 — ADT data-preview **BOŞ CHAR'ı `null` GÖSTERİR** → "null" ekran çıktısı NULL kanıtı DEĞİL (2026-07-28)
- **Belirti:** data-preview / `adt_sql_query` çıktısında bir CHAR kolonu `null` görünüyor. Buna dayanıp `coalesce`/`IS NULL` mantığı kuruluyor.
- **Ölçüm (aynı tabloda):** `WHERE col IS NULL` → **0 satır** · `WHERE col = ''` → **17 satır**. Yani değerler **BOŞ**, NULL değil; `null` sadece görüntüleme biçimi.
- **Neden önemli:** üç değerli mantıkta ikisi farklı davranır — `col <> ''` boş için **FALSE**, NULL için **UNKNOWN** üretir. `CASE`/`WHERE` dallarında bu fark **sessizce başka dal seçtirir**. Gerçek NULL genelde **LEFT JOIN eşleşmemesinden** doğar (o da ayrı bir dal).
- **Kural:** NULL'lığı **ekrandan okuma, `IS NULL` ile ÖLÇ.** Bir CASE'in NULL davranışına güveniyorsan, kaynağa **tuzak notunu yaz** — yoksa sonraki okuyan "NULL kontrolü unutulmuş" deyip `coalesce` ekler ve kasıtlı fallback'i öldürür.
- **Akraba araç sınırları (aynı uç, aynı ders — "400 = endpoint sınırı, dil sınırı değil"):** `adt_sql_query` freestyle ucu `IN ( … )` listesini, 8+ kolonlu `GROUP BY`/`ORDER BY`'ı ve join + çok-`WHEN` `CASE` kombinasyonunu **400**'lüyor. OR-zinciri / az-kolon / tek-`WHEN` ile aşılır. **Aracın reddini dilin reddi sanma;** capability kararını canlı aktivasyonla ver (T9 ile aynı ilke).
  - **+2026-08-11 ölçümü — adlandırılmış-parametreli `currency_conversion( amount => … )` çağrısı bu uçta 400 veriyor.** Denenen **2 biçim**: `target_currency => cast( 'TRY' as waers )` ve çıplak `target_currency => 'TRY'`; ikisi de 400. **KONTROL GRUBU (PATTERN #19):** *aynı* JOIN + *aynı* WHERE, yalnız fonksiyon çıkarılmış hâlde **15 satır döndü** ⇒ reddeden JOIN/WHERE değil, **fonksiyon çağrısının kendisi**.
    ⚠ **İDDİANIN KAPSAMI DAR** (bilerek): kanıtlanan = *bu iki biçim reddedildi*. Kanıtlanmayan = "fonksiyon bu uçta hiç çalışmaz" — başka bir çağrı biçimi (konumsal parametre, `@` host-değişkeni, farklı hata-yönetimi) denenmedi. **Ölçmeden genişletme.** Prior-art araması yapıldı: repoda `currency_conversion` 20 dosyada geçiyor ama **hepsi CDS/AMDP kaynağı içinde** — bu ucun daha önce PB dönüşümüyle koşulduğuna dair kayıt YOK (regresyon değil, ilk temas).
    - **Pratik sonuç:** PB dönüşümünü doğrularken **CDS'in kendi kolonundan oku** (view zaten dönüştürülmüş değeri verir) ya da ABAP tarafında ölç. ⚠ Boşluğu **elle çarpımla doldurma** (ters kotasyon + TCURR faktörü → SATNAV yanığı: 20.000 TRY → −1.032.324).

### T14 — `currency_conversion` **DDIC-based view'de** iki ayna kısıt taşır; **view-entity'de bu kısıtlar YOK** (2026-08-10)

**Kısıt tablosu (üç aktivasyon turuyla ölçüldü, ham hata `DDLS 373`):**

| parametre | KABUL | RET | ham hata |
|---|---|---|---|
| `AMOUNT` | **Columns**, Paths, Parameters | ifade, cast | *"For parameter AMOUNT only Columns,Paths,Parameters can be passed"* |
| `EXCHANGE_RATE_TYPE` | Expressions, **Literals**, Parameters | **KOLON** | *"For parameter EXCHANGE_RATE_TYPE only Expressions,Literals,Parameters can be passed"* |

İkisi **birbirinin aynası**: `amount` kolon İSTER, `exchange_rate_type` kolon KABUL ETMEZ. Birini
düzeltmek diğerini görünür yapar (aktivasyon **ilk hatada iptal eder** → her tur tek bilinmez kapanır;
"diğer parametreler temiz" **İDDİA EDİLEMEZ**).

- **⛔ EN ÖNEMLİ SONUÇ — prior-art'ı kopyalamadan önce VİEW TİPİNE bak.** Aynı sistemde `ZSD001_I_*`
  analitik view'ları `exchange_rate_type`'a `CASE`+**kolon** verip **canlı-aktif** olabilir — çünkü onlar
  **`define view entity`**. DDIC-based (`define view` + `@AbapCatalog.sqlViewName`) aynı kodu **reddeder**.
  Kısıt **view tipine bağlıdır**; "aynı sistemde çalışan örnek var" tek başına kanıt değildir.
- **Pratik sonuç 1 — toplam (ör. vergi dahil tutar) doğrudan çevrilemez.** Çare: bileşenleri **ayrı ayrı**
  çevir ve dışarıda topla (`conv(net) + conv(vergi)`). ⚠ Her çağrı hedef PB ondalığına yuvarladığı için
  sonuç "toplamı bir kez çevirme"den **≤ 0,01 sapar** — bilinçli ödün olarak kaynağa YAZ.
- **Pratik sonuç 2 — kur tipi VERİDEN TÜRETİLEMEZ.** Belgenin kendi kur tipini (`VBRK-KURST` vb.)
  kullanmak DDIC-based'de imkânsız; sabit literal ya da view parametresi olmak zorunda. Parametre eklemek
  klasik tüketiciyi (`SELECT … FROM <sqlview>`, ALV `TYPE TABLE OF <sqlview>`) **kırar** ⇒ klasik rapora
  dokunulamıyorsa **sabit literal tek yol**; bu bir **iş kararıdır**, kullanıcıya sor.
- **Kabul edilenler (aynı turda ölçüldü, DDIC-based'de ÇALIŞTI):** `error_handling => 'SET_TO_NULL'` ✅
  (view-entity'de `SD_EXPRESSION 146` verir — **ters yönde asimetri**) · DTEL cast
  (`cast('TRY' as waers)`, `cast(0 as <CURR_DTEL>)`) ✅ · dış `cast( case … end as <CURR_DTEL> )` ✅ ·
  `coalesce` ✅. Built-in `abap.cuky`/`abap.curr(n,m)` **denenmedi** (DDIC-based'de repo-kanıtı yoktu).
- **Çalışan reçete:**
  ```
  cast( case when <src_cuky> = '<TGT>' then <col_a> + <col_b>
             when <src_cuky> <> '' and <src_cuky> is not null
               then coalesce( currency_conversion( amount => <col_a>, source_currency => <src_cuky>,
                                target_currency => cast( '<TGT>' as waers ), exchange_rate_date => <date_col>,
                                exchange_rate_type => 'M', error_handling => 'SET_TO_NULL' ), 0 )
                  + coalesce( currency_conversion( amount => <col_b>, … ), 0 )
             else 0 end as <CURR_DTEL> )
  ```
- **Denenen ve BAŞARISIZ (tekrar deneme):** `amount => cast( (a+b) as <DTEL> )` · `amount => (a+b)` ·
  `exchange_rate_type => case when <kolon> <> '' then <kolon> else 'M' end`.
- **Ters kotasyon uyarısı:** TCURR'da bir yön **negatif `UKURS`** ile saklanabilir (ör. TR-özel bir tip
  TRY→EUR = −55,04 iken `M` EUR→TRY = +55,04 — **aynı kur**, ters kotasyon). `currency_conversion` bunu
  doğru çözer; **elle çarpım çözmez** (ölçülmüş vaka: 20.000 TRY → −1.032.324). Ayrıca bir kur tipi
  **yalnız tek yönde** günlük bakımlı olabilir ⇒ hedef PB'ye göre farklı tip gerekebilir; hangi
  (tip × yön) çiftinin bakımlı olduğunu **TCURR'dan ölç**, varsayma.
- **@Semantics yan etkisi (klasik ALV):** her çevrilmiş tutar `@Semantics.amount.currencyCode` için bir
  **sabit PB kolonu** ister; DDIC view'a eklenen bu kolonlar `LVC_FIELDCATALOG_MERGE` + `SELECT *` ile
  beslenen ALV'de **kolon olarak görünür ve gizlenemez** (`no_out` için programa dokunmak gerekir).
  Kullanıcıya önceden söyle; alan sırasında tutarların **ardına** koy.
