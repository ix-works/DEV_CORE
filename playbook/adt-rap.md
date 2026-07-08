---
layer: L3
scope: project-wide
type: playbook
applies-to: backend
last-updated: 2026-05-15
status: active
maturity: pilot-in-progress
---

# RAP — View Entity / BDEF / Behavior / Service Definition / Service Binding / Publish

## 32. RAP Obje Zinciri (ADT REST / MCP)

> **Olgunluk uyarısı:** RAP bu projede **ilk kez** uygulanıyor (ORDER pilotu, hafıza
> `project_zsd015-ui-paradigm-all-or-nothing`). Aşağıda **kanıtlanmış** ile
> **kanıtlanmamış (Faz 0 spike doğrulayacak)** açıkça ayrılmıştır. Kanıtlanmamış bir
> adım çalışınca → bu dosya T1 ile güncellenir (ÇALIŞAN YÖNTEM doldurulur).
> Çökerse → DENENEN VE BAŞARISIZ + STOP + kullanıcıya rapor (ADR 0006, pilot GATE).
>
> Stabil kural → L2 [`standards/05-coding-rap.md`](../standards/05-coding-rap.md).
> Reviewer checklist → [`checklists/rap-creation.md`](checklists/rap-creation.md).

### 32.0 ADT Type Kodları

| RAP Objesi | ADT Type | Endpoint kökü |
|---|---|---|
| CDS view entity (I_/C_/R_) | `DDLS/DF` | `/sap/bc/adt/ddic/ddl/sources` |
| Behavior Definition | `BDEF/BDO` | `/sap/bc/adt/bo/behaviordefinitions` |
| Behavior impl. sınıfı | `CLAS/OC` | `/sap/bc/adt/oo/classes` |
| Service Definition | `SRVD/SRV` | `/sap/bc/adt/ddic/srvd/sources` |
| Service Binding | `SRVB/SVB` | `/sap/bc/adt/businessservices/bindings` |

### 32.1 CDS View Entity — ✅ ÇALIŞAN YÖNTEM (KANITLANDI 2026-05-15, ORDER spike)

RAP view entity de DDLS objesidir → **§17/§30 ile aynı 2-step pattern** çalışır.
`ZSD001_I_ORDER` (root interface) + `ZSD001_C_ORDER` (root projection) bu
sistemde **uçtan uca AI ile yaratıldı + aktive edildi** (operatör=0):

```powershell
# 1) reviewer pre-flight (ADR 0006)
python scripts/validators/run_review.py --task rap_cds_creation --artifact <cds>
# 2) shell+PUT (RAP-aware populate; --cwd YOK, PowerShell)
python scripts/populate_cds_views.py --package ZSD001_CLC --transport <TRANSPORT> `
  --source-dir ERP/SD/ZSD001_CLC/cds --only ZSD001_I_ORDER [--force-recreate]
# 3) aktivasyon AYRI adım (script aktive ETMEZ, sadece push)
mcp__sap-adt__adt_activate(name=ZSD001_I_ORDER, object_type=ddls)
# 4) doğrula: adt_get include_source=false → adtcore:version="active"
```

**KRİTİK kurallar (spike'ta kanıtlandı):**
- Root entity'nin projection'ı da **`define root view entity`** olmalı. Aksi:
  `ROOT keyword missing since <I_view> has the root property` → aktivasyon iptal.
- Projection aktivasyonu BDEF yokken **warning** verir ("Transactional Provider
  Contract expected") — read-only spike'ta kabul; BDEF (Faz 2) çözer.
- `populate_cds_views.py` **push eder, aktive etmez** → ayrı `adt_activate`.
- SAP `ddl:source_type="view entity"` olarak tanır, masterLanguage=TR (ADR 0005 D ✓).

### 32.1b DENENEN VE BAŞARISIZ (2026-05-15 spike)

- ❌ `mcp__sap-adt__adt_post_shell(object_type='ddls')` → "Unsupported object
  type: DDLS/DF". **MCP DDLS shell yaratamıyor** → `populate_cds_views.py` kullan.
- ❌ `mcp__sap-adt__adt_post_shell(object_type='srvd')` → "Unsupported object
  type: srvd". MCP destekli liste: class/interface/program/include/functiongroup/
  function/dataelement/domain/table/structure/tabletype/cds/metadataextension/
  accesscontrol/package. **srvd/srvb YOK** (SD/SB için MCP yolu kapalı).
- ❌ `populate_cds_views.py --cwd <PROJECT_ROOT>` (bash) → backslash
  yendi (`<LEGACY_ROOT><PROJECT_NAME>`), `.conn_adt` bulunamadı. **Çözüm:** `--cwd`'yi
  ATLA (zaten proje kökü) + **PowerShell** tool kullan.
- ❌ `adt_get(object_type='tabl', include_source=true)` → `[400] .../source/main`.
  Tablo DDL source MCP wrapper'da çalışmıyor; metadata-only (`include_source=
  false`) çalışıyor. Field adı için tabloyu select eden aktif CDS'i oku.

### 32.1c (eski referans — klasik DDLS 2-step)
1. POST shell `/sap/bc/adt/ddic/ddl/sources` (metadata)
2. LOCK → PUT `/source/main` (asıl DDL) → UNLOCK
3. `activate_object.py --type cds`

Script: `scripts/populate_cds_views.py` (batch) — **RAP-aware** (`validate_sql_view_names()` view-entity'de sqlViewName aramaz, `^ZSD001_(I|C|R|E)_*` adını doğrular; 2026-05-15 reconcile, plan §88).

**Klasik view'dan FARK (KRİTİK):**
- `define root view entity ZSD001_I_ORDER` (NOT `define view zsd015_ddl_...`)
- `@AbapCatalog.sqlViewName` **YOK** (view entity'de yasak — varsa BLOCKER)
- `@AbapCatalog.compiler.compareFilter` view entity'de gereksiz
- Composition: `composition [1..*] of ZSD001_I_ORDERDEST as _Destination`
- Child'da `association to parent ZSD001_I_ORDER as _Voyage on ...`
- Projection: `define view entity ZSD001_C_ORDER as projection on ZSD001_I_ORDER`

### 32.2 Behavior Definition — ✅ WRAPPER FIXED 2026-06-14

Script: `scripts/create_behavior_definition.py` → `sap_client.create_behavior_definition(name, root_entity, implementation_type=Managed, transport, source, activate)`.

**KÖK-FIX 2026-06-14:** wrapper eskiden ÇALIŞMIYORDU (404) — yanlış content-type (`.behaviorDefinition+xml`), yanlış endpoint (`/behaviordefinitions`, `/bo` eksik), yanlış payload (`bdef:behaviorDefinition`) + bozuk kapanış tag. §32.6c kanıtlı reçeteye çevrildi: endpoint `/sap/bc/adt/bo/behaviordefinitions`, CT `application/vnd.sap.adt.blues.v1+xml`, payload `blue:blueSource` (BDEF/BDO) + LOCK/PUT(text/plain, If-Match YOK)/UNLOCK; shell POST + source PUT artık `_request_with_csrf_retry` üzerinden (CSRF self-heal). Throwaway BDEF testi (ZSD001_I_ZZBDEFTEST): shell 201 + source PUT 200 PASS, silindi. **Managed BDEF tek-başına aktivasyon, behavior class henüz yoksa "BEHAVIOR cannot be implemented" verir → BDEF+class BİRLİKTE aktive et (§32.6c step_bactivate).**

- BDEF adı = root entity adı (`ZSD001_I_ORDER`) — SAP zorunlu.
- `--implementation-type Managed`, `--transport <kullanıcı TR>`, `--package ZSD001_CLC`.
- Source: `managed; ... define behavior for ZSD001_I_ORDER ...`.
- **Riziko:** CDS source body'de olduğu gibi (§30.1) wrapper "body ignore" davranışı gösterebilir → 2-step (shell + PUT `/source/main`) gerekebilir. Spike'ta doğrula.

### 32.3 Behavior Implementation Sınıfı — ✅ class push pattern (§19/§26)

`ZCL_SD001_ORDER` → mevcut class push+activate akışı (`push_object.py`, `adt-classes.md` §19/§26). RAP-spesifik fark yok (normal global class, `FOR BEHAVIOR OF ZSD001_I_ORDER`).

### 32.4 Service Definition (SRVD) — ✅ ARAŞTIRILDI (DDLS-twin)

SRVD = DDLS ailesi source objesi → DDLS 2-step ile birebir: endpoint
`/sap/bc/adt/ddic/srvd/sources` (POST shell → LOCK → PUT `/source/main` →
UNLOCK → activate), ADT type `SRVD/SRV`. Source:
```
@EndUserText.label: 'Sefer servisi'
define service ZSD001_UI_ORDER {
  expose ZSD001_C_ORDER;
}
```
`populate_cds_views.py::create_one` mekaniği (CSRF + stateful lock + PUT) sadece
endpoint/content-type değişimiyle kullanılabilir → kalıcı `create_service_definition.py`.

### 32.5 Service Binding (SRVB) + PUBLISH — ✅ ARAŞTIRILDI: REST-SCRIPTABLE (MAKE-OR-BREAK ÇÖZÜLDÜ)

> **Kaynak:** `abap-adt-api` (kanonik ADT client, marcellourbani)
> `src/api/rapgenerator.ts` — 2026-05-15 web araştırması (kullanıcı yönlendirmesi,
> kör deneme yerine). **Publish ADT-native REST → SEGW operatör adımı YOK →
> pilot premisi (RAP yerine SEGW, operatör=0) teknik olarak DOĞRULANDI.**

**Publish service binding (ADT "Publish" butonunun REST'i):**
- `POST /sap/bc/adt/businessservices/odatav2/publishjobs` (V2; V4 = `.../odatav4/publishjobs`)
- Content-Type: `application/xml`
- Accept: `application/xml, application/vnd.sap.as+xml;charset=UTF-8;dataname=com.sap.adt.StatusMessage`
- Body: XML `<adtcore:objectReference adtcore:name="ZSD001_UI_ORDER_O2"/>` (binding adı)

**SRVB yarat:** `POST /sap/bc/adt/businessservices/bindings` (XML: binding type
ODATA, category V2, service definition ref). Create XML implementasyonda kesinleşir.

**Alternatif — RAP Generator REST (tek akışta tüm stack):**
`/sap/bc/adt/businessservices/generators/{genId}` → GET `validation`/`schema`/
`content`/`uiconfig` → `POST {genId}?referencedObject=<CDS>&corrNr=<TR>`
(Content-Type `application/vnd.sap.adt.repository.generator.content.v1+json`).
ADT "Generate OData UI service" sihirbazının REST'i; CDS'ten BDEF+behavior+
SRVD+SRVB üretir. Yüksek seviye; üretilen şekil sihirbaz-standardı.

**Doğrula:** publish sonrası `GET /sap/opu/odata/sap/ZSD001_UI_ORDER_O2/$metadata` = 200.

### 32.6 DENENEN VE BAŞARISIZ YOLLAR
- ❌ MCP `adt_post_shell(object_type='ddls')` ve `('srvd')` → "Unsupported object
  type" (destek listesi sabit). DDLS → `populate_cds_views.py`; SRVD → ham REST.
- ❌ MCP `adt_get(object_type='tabl', include_source=true)` → `[400] /source/main`
  (metadata-only çalışıyor); srvd/srvb MCP GET desteklemiyor.
- ✅ Kör endpoint denemesi YAPILMADI — kullanıcı "ADT/forum araştır" dedi, gerçek
  endpoint `abap-adt-api`'den bulundu (anti-patinaj; canlı SAP'de deneme-yanılma yok).

### 32.6b SPIKE KANITLARI (2026-05-15 — canlı sistem, ÇALIŞAN/BLOKE)

> Ground truth = sistemin `/sap/bc/adt/discovery` dokümanı (content-type'lar
> tahmin değil, sistemden okundu). Araç: `scripts/create_rap_service.py`.

**✅ Service Definition (SRVD) — KANITLANDI, AI-otonom:**
- Endpoint `/sap/bc/adt/ddic/srvd/sources` (DDLS-twin 2-step + activate)
- Content-Type/Accept: **`application/vnd.sap.adt.ddic.srvd.v1+xml`**
- Shell XML kök `srvd:srvdSource` + **`srvd:srvdSourceType="S"`** (S=Definition,
  X=Extension; sistem `/ddic/srvd/sourceTypes`'tan) + `adtcore:type="SRVD/SRV"`
- source/main PUT `text/plain`; activate `/sap/bc/adt/activation`
- `ZSD001_UI_ORDER` (expose ZSD001_C_ORDER) shell 201 → PUT 200 → activate 200 ✓

**✅ Publish endpoint — KANITLANDI REST-native (make-or-break premisi DOĞRU):**
- `POST /sap/bc/adt/businessservices/odatav2/publishjobs{?servicename,serviceversion}`
  (V4: `.../odatav4/publishjobs`) — discovery'de teyitli. SEGW/operatör YOK.

**⚠️ Service Binding (SRVB) create — REST'te BLOKE (tooling detayı, premise blocker DEĞİL):**
- Endpoint `/sap/bc/adt/businessservices/bindings`, Content-Type
  **`application/vnd.sap.adt.businessservices.servicebinding.v2+xml`**
- POST → `400 Session Timed Out` (content-type düzeltildi + `X-sap-adt-sessiontype:
  stateful` eklendi → yine 400). ADT Eclipse'te SRVB sorunsuz; raw REST'te
  stateful oturum protokolü / validation-önce / kesin XML şekli çözülmedi.
- **Açık seçenekler:** (a) RAP Generator REST `/businessservices/generators/
  {genId}` — CDS'ten SRVD+SRVB+publish tek managed akış (SAP-blessed);
  (b) mevcut bir SRVB'nin ADT trace/payload'unu yakalayıp birebir kopya;
  (c) `/businessservices/bindings/validation` + schema endpoint'leriyle gövde
  şeklini çıkar.

**⚠️ SRVB description EDIT de REST'te BLOKE (2026-06-25 kanıt):** Mevcut SRVB'nin
  yalnız `adtcore:description`'ını değiştirmek için: GET 200 → LOCK **200** (handle
  alınır) → PUT **423 Locked** (geçerli lock handle + transport + ETag ile bile).
  Yani create gibi edit de raw REST'ten geçmiyor — SRVB yazımı Eclipse'in stateful
  session-affinity'sini istiyor. **Sonuç:** SRVB description'ı (i) CREATE anında
  `create_rap_service.py --srvb-label` ile doğru ver (kök fix, commit 52124c4), ya da
  (ii) sonradan Eclipse ADT'de elle düzelt. REST PUT/PATCH ile UĞRAŞMA (thrash). LOCK
  200/UNLOCK 200 ile dangling-lock temizlenebilir (session-timeout zaten düşürür).

### 32.6c FAZ 2 KANITLARI (2026-05-15 — BDEF+behavior, ÇALIŞAN)

**✅ Behavior Definition (BDEF) — KANITLANDI AI-otonom:**
- Endpoint `/sap/bc/adt/bo/behaviordefinitions`, Content-Type
  **`application/vnd.sap.adt.blues.v1+xml`**, shell kök `blue:blueSource`
  (ns `http://www.sap.com/wbobj/blue`), `adtcore:type="BDEF/BDO"`
- 2-step (shell + LOCK + PUT source/main text/plain + UNLOCK) — SRVD ile aynı
- BDEF adı = root entity adı (`ZSD001_I_ORDER`) zorunlu

**✅ Behavior class — MCP `class` push (source yüklendi)**; tek başına aktive
EDİLEMEZ ("BEHAVIOR cannot be implemented in class" — BDEF inactive iken).

**✅ BDEF + class BİRLİKTE aktivasyon — ÇALIŞAN YÖNTEM (RAP circular dep):**
- `POST /sap/bc/adt/activation?method=activate&preauditRequested=false`
- Body: `<adtcore:objectReferences>` İKİ ref (bdef uri + class uri) birlikte
- status 200, `activationExecuted="true"` → ikisi de AKTİF (W-uyarılar normal:
  global auth implement edilmemiş, key readonly önerisi)

**⛔ ADR 0005 D — MCP class create EN yaratır (KRİTİK):** `mcp__sap-adt__
adt_post_shell(object_type='class')` objeyi `masterLanguage="EN"` yaratır
(MCP'de language param yok). Behavior class'ı **raw REST** ile yarat: endpoint
`/sap/bc/adt/oo/classes`, Content-Type `application/vnd.sap.adt.oo.classes.v4
+xml`, shell kök `class:abapClass` + `adtcore:masterLanguage="TR"` (script
step_bclass). Yanlışlıkla EN yaratıldıysa: `adt_delete` → raw REST TR yeniden
yarat → BDEF ile birlikte `bactivate`. Her create sonrası
`adt_get include_source=false` ile `masterLanguage="TR"` doğrula (C-RAP-LANG-01).
Hafıza: `feedback_mcp-post-shell-en-master-lang`.

**❌ RAP Generator API — bu on-prem'de YOK:** discovery'de "RAP Üreteci"
workspace boş; `/sap/bc/adt/repository/generators?referencedObject=...` sadece
`filtersupport` link döner, kullanılabilir genId yok. (ABAP-Cloud/yeni-ADT
özelliği; on-prem 2025'te SRVB elle/Eclipse veya stateful-REST.)

**⚠️ SRVB create — TEK KALAN GAP:** `/businessservices/bindings` POST →
"400 Session Timed Out" (content-type + stateful header düzeltildi, yine 400).
On-prem'de generator yok; SRVB için ya derin stateful-REST protokol
reverse-eng ya tek-seferlik Eclipse (developer self-service, operatör DEĞİL).

### 32.6d SONUÇ — MAKE-OR-BREAK KAPANDI (2026-05-15)

**Canlı, çalışan OData V2 servisi: `ZSD001_UI_ORDER_O2`** —
`/sap/opu/odata/sap/ZSD001_UI_ORDER_O2/$metadata` → 200, `xml:lang="tr"`,
EntitySet `ZSD001_C_ORDER` (read-only, projection behavior'sız), V2 JSON OK
(`$top/$inlinecount/$format`), `__count:0` (tablo boş — veri yok, servis sağlam).

- CDS+BDEF+class+SRVD: **AI-otonom** (raw ADT REST, TR).
- SRVB+publish: bu on-prem'de **tek-seferlik Eclipse** (developer self-service;
  Gateway-operatör DEĞİL). Tüm objeler `masterLanguage="TR"`.
- **Productization: SRVB create XML kanıtlandı** (canlı binding raw GET'inden;
  `create_rap_service.py::srvb_xml` artık gerçek template — sonraki sefer otomatik):
  root `srvb:serviceBinding srvb:contract="C1"` ns `.../adt/ddic/ServiceBindings`
  → `srvb:services/srvb:content(version=0001,releaseState=NOT_RELEASED)/
  srvb:serviceDefinition(uri+type=SRVD/SRV+name)` → `srvb:binding(type=ODATA,
  version=V2,category=0)/srvb:implementation`. Content-Type
  `application/vnd.sap.adt.businessservices.servicebinding.v2+xml`.
- Publish endpoint: `POST /sap/bc/adt/businessservices/odatav2/publishjobs
  ?servicename=&serviceversion=0001`, body `<adtcore:objectReferences>`.

**Verdict: ZSD001 RAP backend uçtan uca AI ile geliştirilebilir; SEGW/operatör
bağımlılığı YOK. Pilot premisi tam doğrulandı.**

### 32.6e RAP COMPOSITION ZİNCİRİ + COMBINED ACTIVATION (KANITLANDI 2026-05-15)

> Sonraki RAP işinde bu adımları **aynen** uygula — deneme-yanılma yok.

**1) Child interface view entity** (root DEĞİL):
```cds
define view entity ZSD001_I_ORDERDEST
  as select from zsd015_t_voydes
  association to parent ZSD001_I_ORDER as _Voyage
    on $projection.VoyageNo = _Voyage.VoyageNo
{ key voyage_no as VoyageNo, key destination_port as DestinationPort, ... , _Voyage }
```
**2) Root interface'e composition ekle** (`as select from ... ` ile `{` arası):
`composition [0..*] of ZSD001_I_ORDERDEST as _Destination` + alan listesine `_Destination`.
**3) Projeksiyonlar:** root projection (root) → `_Destination : redirected to
composition child ZSD001_C_ORDERDEST`; child projection (root DEĞİL) →
`_Voyage : redirected to parent ZSD001_C_ORDER`.

**4) Mevcut AKTİF root CDS güncelleme:** `mcp__sap-adt__adt_push_source
(object_type='ddls')` ile **in-place** (DELETE yok). `populate_cds_views
--force-recreate` KULLANMA → DELETE eder, root'a bağlı BDEF/servis cascade kırılır.
Yeni child CDS'ler: `populate_cds_views --only A,B` (force'suz).

**5) ⚠️ MCP reviewer_timeout:** `adt_push_source` iç reviewer'ı timeout edip
`verdict=BLOCKER, 0 blocker/0 warning, skip_reason=reviewer_timeout` döndürebilir
(gerçek ihlal DEĞİL). Çözüm: o artifact için `run_review.py --task rap_cds_creation`
**manuel PASS** ise → `skip_reviewer=true` ile tekrar push (ADR 0006 dokümante
istisna: manuel reviewer sağlandı). Commit mesajında belirt.

> **⏳ BAYAT (2026-06-18):** Bu timeout'un kök-nedeni bulunup düzeltildi — reviewer subprocess **stdin-deadlock**'u (`feedback_mcp-stdio-subprocess-deadlock`: stdin=DEVNULL + timeout 30s; **✅ 2026-06-11 doğrulandı** — restart sonrası reviewer saniyeler içinde PASS, timeout YOK). Bu workaround **eskidi** → `/mcp restart` sonrası `reviewer_timeout` beklenmez; yine görülürse yeni bir sorundur (körü körüne `skip_reviewer=true` yapma).

**6) Combined activation (mutual composition/redirect dep):** 4 CDS source'u
inactive push et → **tek** `POST /sap/bc/adt/activation?method=activate&
preauditRequested=false` body'de **dört** `<adtcore:objectReference
uri="/sap/bc/adt/ddic/ddl/sources/<lower>" name="<UPPER>"/>` →
`create_rap_service.py --step cdsactivate`. SAP graph'ı tek seferde çözer
(BDEF+class `bactivate` ile aynı mantık). W-uyarı "Transactional Provider
Contract expected" = projection behavior yokken normal (9b çözer).

**7) BDEF managed composition + child behavior:**
```
define behavior for ZSD001_I_ORDER ... { ... association _Destination { create; }
  define behavior for ZSD001_I_ORDERDEST alias VoyageDest
  persistent table zsd015_t_voydes
  lock dependent by _Voyage authorization dependent by _Voyage
  { create; update; delete; field ( readonly ) VoyageNo; association _Voyage;
    mapping for zsd015_t_voydes { ... } } }
```
**Projection behavior = AYRI BDEF** (adı = projection root `ZSD001_C_ORDER`):
`projection; define behavior for ZSD001_C_ORDER { use create; use update;
use delete; use association _Destination { create; } } define behavior for
ZSD001_C_ORDERDEST { use create; use update; use delete; use association _Voyage; }`
Numbering (NR) + validation = behavior-class **local handler** (CCIMP include) —
9b alt-adımı (ayrı; kullanıcı NR objesi domaini).

### 32.6f BDEF child = SIBLING (T1 — 2026-05-15)

❌ Child `define behavior for <I_child>` parent'ın `{ }` BLOĞU İÇİNE yazılırsa:
`"behavior" is not expected here` + `"define|foreign|scalar" was expected, not "}"`.
✅ ÇALIŞAN: child `define behavior` parent'ın kapanış `}`'sından SONRA **ayrı
üst-seviye statement** (sibling). `composition`/`association _Destination` parent
bloğunda kalır; child bloğu bağımsız (`persistent table`, `lock dependent by
_Voyage`, `authorization dependent by _Voyage`, `association _Voyage`, kendi
`mapping`). Projection BDEF zaten 2 ayrı `define behavior` (doğru örnek).

### 32.6g SORUMLULUK PAYLAŞIMI — AI vs KULLANICI (yöntem netliği)

> Sonraki RAP/modül işinde kim neyi yapar — net.

| Adım | AI (otonom, ADT REST/script) | Kullanıcı (tek-seferlik / manuel / domain) |
|---|---|---|
| CDS interface/projection/composition | ✅ tüm zincir (populate_cds_views + cdsactivate) | — |
| BDEF interface + projection (managed, composition, child) | ✅ (create_rap_service.py bdef + pbactivate) | — |
| Behavior class skeleton + (numbering/validation local handler) | ✅ source; CCIMP local handler = 9b | — |
| **NR objesi `ZSD001_VN`** (number range) | ❌ dokunmaz — sadece FM ile **tüketir** | ✅ NR objesini **kullanıcı yaratır/yönetir** (domaini) |
| Service Definition (SRVD) | ✅ tam otonom (ADT REST) | — |
| **Service Binding (SRVB) + publish** | ✅ **TAM OTONOM** (2026-05-19 R2'de gap kapandı, §32.6l): `create_rap_service.py --step srvb → srvbactivate → publish` | — (Eclipse el adımı ARTIK GEREKMİYOR) |
| ADT logon dili / original language | ✅ raw REST shell `masterLanguage=TR` | ✅ Eclipse'te yarattığında **logon dili TR** olmalı; EN kaçarsa **SE03**'te düzelt (C-RAP-LANG-01) |
| Freestyle UI5 (kod) | ✅ tüm webapp | — |
| UI lokal koşum / görsel doğrulama | ❌ npm/browser koşamaz | ✅ `npm install`+`npm start`, tarayıcı basic-auth, ekran teyit |
| SAP'de veri/sonuç doğrulama | ✅ OData GET ile | ✅ SE80/SE16/tarayıcı ile bağımsız teyit (kullanıcı tercihi) |

**Özet (2026-05-19 güncel):** AI = tüm Z RAP objeleri + SRVD + **SRVB +
publish** + UI kodu, uçtan uca, TR. Kullanıcı = NR objesi domaini + UI
lokal koşum + bağımsız SAP doğrulama. SEGW-operatör **ve** SRVB-Eclipse
el adımı **hiç yok** (§32.6l).

### 32.6h CCIMP BEHAVIOR HANDLER (determination/validation) — KANITLANDI 2026-05-15

> RAP managed BO'da numbering/validation/determination = behavior-class **CCIMP
> (Local Types) local handler** (`lhc_*`). Bu pattern KANITLANDI.

**1) BDEF'te bildir:** `determination setVoyageNo on save { create; }` /
`determination setAdmin on save { create; update; }` /
`validation valX on save { field ...; create; update; }`.
**2) CCIMP source** (versiyonlu: `ERP/<pkg>/classes/<CLASS>.ccimp.abap`):
`CLASS lhc_Voyage DEFINITION INHERITING FROM cl_abap_behavior_handler.
PRIVATE SECTION. METHODS get_global_authorizations FOR GLOBAL AUTHORIZATION
IMPORTING REQUEST requested_authorizations FOR Voyage RESULT result.
METHODS setVoyageNo FOR DETERMINE ON SAVE IMPORTING keys FOR Voyage~setVoyageNo.
... ENDCLASS. CLASS lhc_Voyage IMPLEMENTATION. ... ENDCLASS.`
(alias = BDEF alias; EML `READ/MODIFY ENTITIES OF <i_view> IN LOCAL MODE
ENTITY Voyage ... %tky`). `authorization master ( global )` varsa
`get_global_authorizations` (boş gövde = permissive) ZORUNLU, yoksa W→E.
**3) CCIMP push:** class lock (stateful) → `PUT /sap/bc/adt/oo/classes/<cls>/
includes/implementations` (text/plain, lockHandle+corrNr) → unlock
(`create_rap_service.py --step ccimp`). CCDEF = `/includes/definitions`.
**4) Activate:** `pbactivate` (interface+projection BDEF + class birlikte) —
CCIMP class'ın parçası, ayrı aktive edilmez.
**5) Numbering (KR-VOY-001):** `CALL FUNCTION 'NUMBER_GET_NEXT' EXPORTING
nr_range_nr='01' object='ZSD001_VN'` — NR objesi **kullanıcı domaini** (AI
yaratmaz, sadece FM ile tüketir; yoksa runtime hata → kullanıcı yaratır).
W "secondary key ID covered/not used" = benign perf ipucu.

### 32.6i e2e CRUD KANITLANDI + det/val izolasyon (T1 — 2026-05-15)

✅ **Composition deep-create canlı servise ÇALIŞIYOR**: `POST /sap/opu/odata/
sap/<binding>/<C_root>` JSON `{ ...header..., "to_Destination": {"results":
[{...child...}]} }` → 201 (nav property V2'de **`to_<assoc>`** = SADL prefix,
`_<assoc>` DEĞİL). OData CSRF servisin kendi GET'inden.

**Det/Val dump teşhis zinciri (T1):**
- `BEHAVIOR_CONTRACT_VIOLATION CC/C:EMPTY_UPDATE` → determination KEY alanı
  `MODIFY..UPDATE` etmiş (EML-UPDATE ≥1 NON-KEY alan ister). Key set =
  early-numbering/mapped, asla determination-UPDATE.
- `numbering : managed` sadece UUID/RAW16 (ABP_BEHV_PID); NR-objesi CHAR key
  ile uyumsuz → managed-numbering KULLANMA, NR = ayrı (kullanıcı domaini).
- `RAISE_SHORTDUMP / LCX_ABAP_BEHV_DETVAL_ERROR` = determination/validation
  handler runtime patladı (jenerik). **Strateji: BDEF'i SAF CRUD'a indir
  (det/val çıkar) → e2e YEŞİL doğrula → det/val'i TEK TEK, izole, her biri
  ayrı aktive+test ile geri ekle.** Çalışan CRUD ≠ çalışan det/val; ayır.
- **İzolasyon sonucu (kanıt):** valCutoff/valDestinations/valDeleteGuard
  (READ/SELECT + failed/reported) → temiz, e2e 201. **DETVAL dump'ın TEK sebebi
  `setAdmin` = determination içinde `MODIFY ENTITIES UPDATE`** (kendi entity'sine).
  Determination'da MODIFY-UPDATE kırılgan; audit-autofill için ya CDS
  `@Semantics` managed-admin (TEK timestamp alanı gerekli — date+time ayrıksa
  oturmaz) ya da hiç (iş kuralı değil). setAdmin AI kapsamından çıkarıldı.
  → **GÜNCELLEME 2026-05-19 (SUPERSEDE):** setAdmin geri eklendi ve
  KANITLANDI. Dump'ın kökü guard'sız self-MODIFY'ın on-save det'i
  döngüsel tetiklemesiydi ("Infinite loop ... cyclical triggering of
  on-save determinations"). Çözüm = **idempotent guard** (instance
  `DATA mt_done` LUW-scope; işlenen anahtar 2. pas'ta CONTINUE → MODIFY
  yok → döngü kırılır) + `IN LOCAL MODE` + `UPDATE FROM %control`.
  e2e: create→created_*+updated_*, update→updated_* (created_* korunur),
  root+child. `with additional save` denendi → early-numbering'de
  `create-*` component BOŞ, create admin yazılmaz (kullanma). Tam
  pattern + standart: `ui-backend-rap.md` §F · `standards/05` §9A.
- **Validasyon enforce kanıtı:** destination'sız create → **400** + TR mesaj
  ("...KR-VOY-004"); destination'lı → 201. Validasyonlar gerçekten reddediyor.

### 32.6j Early numbering (managed) + MCP lock-cache bug — KANITLANDI 2026-05-15 (T1/T10)

> KR-VOY-001 NR object'i (CHAR key, ZSD001_VN) ile **managed BO early
> numbering** nihai çözüm. Önceki *determination* yöntemi DETVAL-dump
> veriyordu (§32.6i); doğru construct budur.

**1) BDEF — `early numbering` keyword ZORUNLU.** `earlynumbering_create`
handler'ı yazıp BDEF'te `early numbering` bildirmezsen aktivasyon:
`The operation "CREATE" is not activated for entity "<ent>"` (CCIMP
satırını gösterir, yanıltıcı). Düzeltme — root behavior characteristic:
```
define behavior for ZSD001_I_ORDER alias Voyage
persistent table zsd015_t_voyage
lock master
authorization master ( global )
early numbering            "<-- BU SATIR; yoksa CREATE-not-activated
{ create; update; delete; ... }
```
**2) Handler (CCIMP, lhc_, INHERITING cl_abap_behavior_handler):**
`METHODS earlynumbering_create FOR NUMBERING IMPORTING entities FOR
CREATE Voyage.` Gövde: consumer numara verdiyse koru (idempotent,
`mapped-voyage` %cid+%key) → yoksa `CALL FUNCTION 'NUMBER_GET_NEXT'
nr_range_nr='01' object='ZSD001_VN'` → `mapped-voyage` (%cid+VoyageNo).
Hata → `failed`+`reported` (new_message_with_text). **determination
DEĞİL** (key-set determination = BEHAVIOR_CONTRACT_VIOLATION).
**3) Aktivasyon:** önce BDEF (i+c) tek aktive (create aktif olsun) →
sonra `pbactivate` (bdef+bdef+class). CDS değişince BDEF re-activation
ister; sıra: CDS → BDEF → class. e2e: VoyageNo'suz POST → 201, numara
NR'dan atanır (kanıt: `7500000016`).
**4) calculated CDS alanı (BookingCount/DemorageDate vb.) BDEF'te
`field ( readonly )` ile bildirilmez** — assoc/expression alanları
otomatik read-only (PartnerName pattern'i). Bildirirsen gereksiz; key
olmayan child key (`DestinationPort`) için ise `field ( readonly :
update )` doğru (W "should be flagged readonly" kapatır + B.4 zorlar).

**MCP `adt_push_source` brand-new DDLS lock-cache bug (T10):**
Hiç olmayan bir CDS'i ilk kez `adt_push_source` ile yaratınca
`[423] ExceptionResourceInvalidLockHandle` + "SAP did not return
CORRNR" — MCP server stale lock handle'ı cache'leyip her çağrıda
AYNI handle'ı döner (dakikalar sonra bile, deterministik). Retry =
patinaj. **Workaround:** `python scripts/populate_cds_views.py
--package ZSD001_CLC --transport <TR> --source-dir ERP/SD/<pkg>/cds
--only <NAME> --force-recreate --cwd <root>` (bağımsız lock flow) →
sonra `mcp adt_activate <NAME> ddls`. Mevcut obje update'inde bug YOK
(adt_push_source normal çalışır). Reviewer bunu yakalayamaz = known
tooling blind spot; çözüm script-fallback.

> **⏳ BAYAT-adayı (2026-06-18, teyit-bekliyor):** `push_object` upload-failure'da artık unlock ediyor (`feedback_push-failure-stale-lock-persistent-session` kök-fix) → `/mcp restart` taze handle verir. Bu workaround'a hâlâ ihtiyaç olup olmadığı **restart sonrası canlı-teyit** ile değerlendirilmeli (memory "verify before assert" uyarısı taşır — "FIXED" deme); teyit edilince kaldır.

### 32.6k Read-only rapor consumption layer (T1 — 2026-05-19, R2 CONTAINER_REPORT)

> Read-only RAP raporu (BDEF/behavior/NR YOK). I_ + C_ iki katman.
> İki aktivasyon hatası → düzeltildi; pattern KANITLANDI.

**✅ ÇALIŞAN YÖNTEM:**
- **Interface `ZSD<nnn>_I_<RPT>`** = `define view entity ... as select
  from <base/std tablo> ... left outer join <I_ view'lar>`. Join'lerde
  reuse edilecek RAP view'lar **interface** (`as select from`) olmalı —
  `ZSD001_I_ORDER`/`_ORDERDEST` evet, `ZSD001_C_*` HAYIR. Assoc ile
  çözülen ad alanları (DeparturePortName/LinePartnerName) interface'te
  element değil → ilgili text/VH view'ı (`ZSD001_I_PORTVH`,
  `ZSD000_I_BPNAME`) **direkt join**'le (projeksiyonun assoc target'ı).
- **Consumption `ZSD<nnn>_C_<RPT>`** = `define view entity ... as
  **select from** ZSD<nnn>_I_<RPT> { key ...; ... }`. **`as projection
  on` DEĞİL** (read-only'de BO yok).
- Aktivasyon sırası: I_ → C_ (her biri populate_cds_views.py
  --force-recreate + `mcp adt_activate ddls`). Search-help "not
  inherited" W'leri zararsız (read-only).

**❌ DENENEN VE BAŞARISIZ:**
1. Interface'te join kaynağı olarak `ZSD001_C_ORDER`/`_ORDERDEST`
   (projeksiyon reuse iştahı) → aktivasyon: **"Projection Views are not
   allowed as base object for this entity type."** Düzeltme: I_ view'a
   geç, ad alanlarını PORTVH/BPNAME direkt join.
2. C_ katmanı `as projection on ZSD001_I_...` → aktivasyon:
   **"Transactional Projection View must be part of a business
   object."** (`as projection on` = transactional, BDEF/BO zorunlu).
   Düzeltme: `as select from` düz consumption view entity.

**T10 — reviewer yakalayabilir miydi? EVET (statik):** ikisi de regex'le
yakalanır → `check_rap_readonly_consumption.py` eklendi (rap_cds_creation
chain): (a) `define view entity` (projection değil) gövdesinde join'de
`ZSD\d{3}_C_` adı = BLOCKER; (b) dosya adı `ZSD\d{3}_C_*` + içerik `as
projection on` + aynı isimde BDEF yok = BLOCKER.

### 32.6l SRVB+publish TAM OTONOM — Eclipse gap KAPANDI (T1/T2 — 2026-05-19, R2)

> §32.6d/§32.6g'deki "SRVB = tek-seferlik Eclipse" iddiası **SUPERSEDED**.
> R2 CONTAINER_REPORT'ta SRVB→activate→publish uçtan uca raw REST ile
> kanıtlandı. Sonraki RAP servisinde Eclipse el adımı YOK.

**✅ ÇALIŞAN SIRA (read-only veya transaksiyonel, fark etmez):**
1. `--step srvb` → `POST /sap/bc/adt/businessservices/bindings`
   (Content-Type `...servicebinding.v2+xml`, `X-sap-adt-sessiontype:
   stateful`, corrNr=TR) → **201** (tarihsel "400 Session Timed Out"
   gap'i artık yok; gövde `create_rap_service.py::srvb_xml` canlı
   ORDER'dan grounded).
2. `--step srvbactivate` (**YENİ adım**) → create `bindingCreated=
   "false"`/`version="inactive"` döner; publish job aktif binding
   ister. Kanonik `POST /sap/bc/adt/activation?method=activate`
   objectReference URI=`/sap/bc/adt/businessservices/bindings/<name
   lower>` (SRVD/BDEF/CDS'le **aynı** endpoint) → 200
   `activationExecuted="true"`.
3. `--step publish` → `POST /businessservices/odatav2/publishjobs
   ?servicename=&serviceversion=0001` → SEVERITY=OK "activated
   locally". (srvbactivate atlanırsa publish: "Service Binding ...
   does not exist" — yanıltıcı; gerçek sebep inactive binding.)
4. `--step verify` → `/sap/opu/odata/sap/<SRVB>/$metadata` = 200.

**❌ DENENEN VE BAŞARISIZ:** srvb create sonrası direkt publish →
"Service Binding does not exist" (version 0001). Düzeltme = araya
srvbactivate. Reviewer yakalayamaz (canlı-servis state, statik değil) =
known sequencing rule; çözüm = script adımı zorunlu sıra.

**Çoklu-servis + modül-bağımsız reuse:** `create_rap_service.py` parametrik
— `--srvd-name --srvb-name --expose-root --srvd-label --expose-extra
--package` (+ `--transport`). Default = ORDER/ZSD001_CLC (geriye uyumlu).
**Başka modül/paket için `--package` ZORUNLU** (yoksa objeler ZSD001_CLC'ye
yaratılır — sessiz yanlış-işlem). Her yeni app kendi SRVD/SRVB'sini alır.
Kanıt: `ZSD001_UI_CONREP` / `ZSD001_UI_CONREP_O2` (expose
`ZSD001_C_CONTAINER_REPORT` + BOOKINGVH + BPNAME + VKORGVH + SHIPTYPEVH),
$metadata 200 / 46 KB, 2026-05-19.

**Modül-agnostik düzeltme (2026-05-19, izolasyon denetimi):** 3 RAP-script
ZSD-prefix varsayımından arındı → başka modül (ZMM/ZFI/ZEWM…) için de
doğru: (a) `create_rap_service.py` `--package` override; (b) `populate_
cds_views.py` `RAP_VE_NAME_PATTERN` `^Z[A-Z]{2,4}\d{3}_(I|C|R|E)_` (klasik
ZSD001 sqlView whitelist bilinçli olarak ZSD001-katı kaldı — Sprint-3
legacy guard, yeni iş RAP); (c) `check_rap_readonly_consumption.py`
regex `Z[A-Z]{2,4}\d{3}` (eskiden ZMM/ZFI'yi sessiz atlardı = false-
negative; artık yakalıyor). ZSD001 regresyonsuz (chain PASS 0/0). Klasik
namespace whitelist + `check_object_in_correct_pkg.py` PACKAGE_EXCEPTIONS
hâlâ statik = bilinen sınırlama; `.rules.md`'den okuma ADR 0003 Adım-6
(yeni paket bootstrap'ı dar etki: sadece cross-prefix isimli obje).

### 32.7 KRİTİK NOTLAR

- Her SAP yazma öncesi `run_review.py --task rap_cds_creation|rap_bdef_creation|rap_service_binding` (ADR 0006).
- View entity'de `@AbapCatalog.sqlViewName` = BLOCKER (klasik'in tam tersi).
- BDEF adı ≠ root entity adı → SAP aktivasyon hatası.
- Aktivasyon dependency sırası: interface view → projection → BDEF → behavior class → SD → SB → publish. Her adım `version="active"` doğrulanır.
- Transport: kullanıcının verdiği aktif TR; **yenisi yaratılmaz** (ADR 0005 C).
- TADIR/rename riski (§30.9): view entity'de sqlViewName olmadığı için klasik orphan sorunu yok; ama yanlış isimle aktive edilen DDLS yine workbench DELETE + TR release ister.

### 32.8 Script ↔ Playbook

| Script | İşlev |
|---|---|
| [`scripts/populate_cds_views.py`](../scripts/populate_cds_views.py) | View entity batch (RAP-aware pre-flight) |
| [`scripts/create_behavior_definition.py`](../scripts/create_behavior_definition.py) | BDEF |
| [`scripts/create_behavior_implementation.py`](../scripts/create_behavior_implementation.py) | Behavior pool sınıfı |
| [`scripts/create_metadata_extension.py`](../scripts/create_metadata_extension.py) | DDLX metadata extension |
| `scripts/push_object.py` / `activate_object.py` | Class push + aktivasyon |

---

## 33. RAP "FAÇADE" deseni — unmanaged read-only entity + static function/action (KANITLANDI 2026-06-03, ZSD001 spike)

> **§32 managed-BO-on-Z-table'dan FARKLI.** Bu desen: veri STANDART objelerde (VBAK/VBAP),
> yazma SAP released BO'ya (`I_SalesOrderTP` EML) gider → kendi persistence/lock/numbering YOK.
> Sorgu = consumption CDS; iş operasyonları = **static function (okuma→V2 GET FI)** /
> **static action (yazma→V2 POST FI)**, gövde reuse class'a (`Z*_CL_*`) delege. Klasik SEGW
> function-import muadili. **Canlı kanıt:** ZSD001 GetBalance function → `$metadata` FunctionImport → GET 200.

### Obje zinciri (sıra)
1. **Interface root view entity** — `define root view entity Z..._I_X as select from <std>` (join'ler).
   ⚠️ Projeksiyon root ise temel de **`root`** olmalı (yoksa "ROOT keyword not valid"). View entity → sqlViewName YOK.
2. **Projection** — `define root view entity Z..._C_X as projection on Z..._I_X`.
3. **Abstract entity'ler** — `define abstract entity Z..._I_*_P/_R` (action/function param+result). Result `[0..*]` → collection döner; **DDIC TT gerekmez**. (populate_cds_views RAP-skip: td_spec + sqlViewName uygulanmaz.)
4. **Base behavior (INTERFACE'te)** — `unmanaged implementation in class zcl_..._behv; define behavior for Z..._I_X authorization master ( global ) { static function GetX parameter ..._P result [0..*] ..._R; static action DoY parameter ..._P result [1] ..._R; }`
   - ⛔ **`strict ( 2 )` KULLANMA** read-only static-only'de → "every entity must be lock master/dependent" hatası (lock yok). (strict warning'i kabul.)
   - ✅ **`authorization master ( global )` ŞART** — `get_global_authorizations` handler için (yoksa "not an entity with authorization check").
   - READ implement edilmedi → sadece W (query-only normal).
5. **Behavior class** — global: `CLASS zcl_..._behv DEFINITION PUBLIC ABSTRACT FINAL FOR BEHAVIOR OF Z..._I_X. ENDCLASS. CLASS ... IMPLEMENTATION. ENDCLASS.` · ccimp (Local Types): `lhc_X` handler — `METHODS GetX FOR READ IMPORTING keys FOR FUNCTION X~GetX RESULT result.` (function) / `... FOR MODIFY ... FOR ACTION ...` (action) + `get_global_authorizations`. `%param-<Field>` ile sonuç doldur.
6. **Projection behavior** — `projection; define behavior for Z..._C_X { use function GetX; use action DoY; }`.
7. **SRVD** expose `Z..._C_X` → **SRVB `_O2`** (V2) → **activate → publish** → `$metadata` FunctionImport.

### Tooling (create_rap_service.py — modül-agnostik, ZSD001 spike'ta parametrize edildi)
```powershell
# BDEF (interface) — NOT: lib create_behavior_definition.py KÖK-FIX'lendi (2026-06-14, §32.6c:
#   doğru endpoint /sap/bc/adt/bo/behaviordefinitions + blues.v1+xml). Pipeline'da entegre
#   akış için create_rap_service.py --step bdef tercih edilir (SRVD/SRVB/publish ile zincir).
python scripts/create_rap_service.py --step bdef    --bdef-name Z..._I_X --bdef-source <bdef> --package <PKG> --transport <TR>
python scripts/create_rap_service.py --step bclass  --bclass-name ZCL_..._BEHV --bdef-name Z..._I_X --package <PKG> --transport <TR>
python scripts/create_rap_service.py --step ccimp   --bclass-name ZCL_..._BEHV --ccimp-source <ccimp> --transport <TR>
python scripts/create_rap_service.py --step bactivate --bdef-name Z..._I_X --bclass-name ZCL_..._BEHV --transport <TR>   # interface bdef + class birlikte
# projection bdef:
python scripts/create_rap_service.py --step bdef    --bdef-name Z..._C_X --bdef-source <proj_bdef> --package <PKG> --transport <TR>
python scripts/create_rap_service.py --step pbactivate --bdef-name Z..._I_X --bclass-name ZCL_..._BEHV --transport <TR>  # I_+C_ bdef + class (proj = I→C türetir)
# servis:
python scripts/create_rap_service.py --step srvd --srvd-name Z..._UI_X --expose-root Z..._C_X --srvd-label "..." --package <PKG> --transport <TR>
python scripts/create_rap_service.py --step srvb --srvb-name Z..._UI_X_O2 --srvd-name Z..._UI_X --package <PKG> --transport <TR>
python scripts/create_rap_service.py --step srvbactivate --srvb-name Z..._UI_X_O2 --transport <TR>
python scripts/create_rap_service.py --step publish --srvb-name Z..._UI_X_O2
python scripts/create_rap_service.py --step verify  --srvb-name Z..._UI_X_O2   # $metadata=200
```
> ⚠️ MCP `adt_activate` `bdef` tipini DESTEKLEMEZ → bdef aktivasyonu create_rap_service.py (bactivate/pbactivate) ile. CDS/class/SRVD/SRVB için MCP adt_activate OK.

### V2 çağrı kuralı (UI eşlemesi için kritik)
String function-import parametresi **tek-tırnaklı**: `GetBalance?IvKunnr='0000300000'&IvBukrs=''`. Tırnaksız → `400 Invalid function import parameter type ... Expected Edm.String`.

### Tuzaklar (hepsi spike'ta yaşandı + çözüldü)
| Belirti | Çözüm |
|---|---|
| `create_behavior_definition.py` → 404 (TARİHSEL — KÖK-FIX 2026-06-14, §32.6c) | Lib artık doğru endpoint (`/bo/behaviordefinitions`+blues.v1); pipeline'da `create_rap_service.py --step bdef` |
| "ROOT keyword not valid" | Projection root ise interface de `define root view entity` |
| "every entity must be lock master/dependent" | `strict ( 2 )` kaldır (read-only static-only) |
| "not an entity with authorization check" | bdef'e `authorization master ( global )` ekle |
| MCP adt_activate "Unsupported object type: bdef" | bdef aktivasyonu create_rap_service.py |
| currency annotation BLOCKER (`'Waerk'`) | view entity'de element-adı doğru; `check_cds_currency_reference.py` düzeltildi |
| abstract entity td_spec/sqlViewName blok | `populate_cds_views.py` RAP-skip'e abstract entity eklendi |
| FI param 400 | string param tek-tırnaklı |
| action sonucu boş döner (Success:false, alanlar '') | result satırına **`%cid = keys-%cid`** ekle (action correlation; function'da gerekmez) |
| abstract result'ta `kwmeng`/`wrbtr` → "reference information missing or data type wrong" | quantity/amount **semantik referans ister** (unit/currency elemanı). Function result'ta gereksiz → **düz `abap.dec(13,3)`/`abap.dec(15,2)`** kullan (BALANCE_R deseni; persist/UI yok, sadece sayı) |
| reusable reuse-class push → **plaintext parola** (hardcoded `authenticate( password = ... )`) guard'a takıldı | ADR 0005: parola source'a YAZILMAZ. Same-system OData self-call için **oturum-tabanlı kimlik** (SM59 current-user/assertion destination → `create_by_destination`). Bu sistemde SSO2-issuing FM (SUSR_CREATE_LOGON_TICKET2) YOK → operasyon **PENDING stub + net 'E' mesaj** (sessiz bozma yok) + deferred-triggers kaydı. Kontratı/diğer ops'u bloke etme |

> ✅ **static ACTION da KANITLANDI** (CreateSalesOrder POST→200; **gerçek sipariş yaratıldı VBELN 1000000028**, 2026-06-03). **unmanaged-no-saver action'ı TOLERE EDER** ("SAVER not implemented" sadece W). Gerçek EML (`I_SalesOrderTP` released BO) action handler içinde çağrılır; **kendi persistence yok → saver implement edilmez**.
>
> ⛔ **COMMIT ENTITIES behavior handler İÇİNDE YASAK** → `500 BEHAVIOR_ILLEGAL_STATEMENT`. Released BO'ya EML MODIFY yap, **COMMIT ETME** — OData modifying-request (action POST) sonunda framework commit eder (SEGW/DPC'deki gibi; sipariş gerçekten DB'ye yazıldı, doğrulandı VBKD-bstkd).
>
> ⛔ **KLASİK DB-COMMIT (`COMMIT WORK`/`ROLLBACK WORK`/`BAPI_TRANSACTION_COMMIT`/`_ROLLBACK`) RAP handler VE handler'dan çağrılan HELPER class içinde YASAK** → runtime `BEHAVIOR_ILLEGAL_STATEMENT` dump (SAPLBAPT), bağlantı reset, UI "HTTP request failed" (dump mesajı yutar). **Static-check/syntax/ATC/abaplint/bug-gate GEÇER → yalnız ilk gerçek RUNTIME create/action testinde çıkar.** Kanıt: ZSD001 `create_transport_doc` (BAPI_SHIPMENT_CREATE+BAPI_TRANSACTION_*), 3 bug-gate+syntax+ATC atladı, ilk create testinde dump (2026-06-23). **Bu hata gate'siz prose'la yıllarca kaçar → deterministik gate ŞART** (`check_no_rap_commit` / BE-26 / ADR 0019).
>
> ✅ **DOĞRU DESEN — commit gerektiren klasik BAPI'yi RAP'ten çağırma (AYRI LUW):** BAPI (`BAPI_SHIPMENT_CREATE`/VT01N, `SD_SCDS_CREATE`/VI01 `i_opt_commit='X'`, vb.) + `BAPI_TRANSACTION_COMMIT/ROLLBACK`'i bir **Z RFC-enabled FM**'e sar → caller `CALL FUNCTION 'Z..._FM_...' DESTINATION 'NONE'` ile çağırır. `'NONE'` ayrı roll-area/LUW açar → `COMMIT WORK` orada **LEGAL**. Class'ta commit YOK; **commit yalnız RFC-FM'de**. Sonuç/mesajlar FM'in `EXPORTING`/`TABLES`'ından döner (çoklu BAPIRET2 → hepsi toplanır). Kanonik örnek: `ZSD001_FM_SHIPMENT_CREATE` (FG `ZSD001_FG_SHIPMENT`) + caller `ZCL_SD001_BOOKING_API->create_transport_doc`. **2 tuzak:** (a) FM **Remote-Enabled** olmalı (SE37 "Processing Type"; ADT'den 400, manuel tık) yoksa runtime `CALL_FUNCTION_NOT_REMOTE`; (b) FM TABLES paramı ADT-push'ta `TYPE <struct>` (NOT `STRUCTURE`); (c) caller `EXCEPTIONS system_failure=1 MESSAGE <var>` → `<var>` **char-like** (C/N/D/T), `STRING` değil.
>
> ⚠️ **Late-numbering açığı:** `I_SalesOrderTP` sipariş no'yu SAVE anında atar → action handler (interaction faz) `mapped-salesorder` BOŞ alır → V2 response'ta yaratılan numara **senkron dönmez** (Success=X ama Salesorder=''). Sipariş yine de yaratılır. **UI çözümü (Faz 1):** create success sonrası PO referansıyla (`purchaseorderbycustomer`) `C_SO_ITEM` re-query → numarayı bul. (SEGW/DPC bunu yapabiliyordu çünkü RAP-handler değil, normal ABAP context'te commit+read ediyordu.)
>
> ✅ **TAM OPERASYON SETİ KANITLANDI (ZSD001 Faz 1b, 2026-06-03):** 7 operasyon tek `_O2` serviste — **GET function** (GetBalance, GetCustomerDefaults, SimulatePricing) + **POST action** (CreateSalesOrder, UpdateSalesOrder, RejectSalesItems, CreateDeliveryAddress). **Kural: okuma=function (UI `read()`/GET korunur), yazma=action (POST).** (Update/Reject dahil COMMIT semantiği için tek-ev = yukarı ⛔ "COMMIT ENTITIES behavior handler İÇİNDE YASAK".) Çoklu operasyon eklerken: her biri base+proj bdef'e satır + ccimp handler; bdef değişince **her ikisini de re-push + bactivate+pbactivate + republish**. Sonuç entity'leri paylaşılabilir (Update → CreateSalesOrder'ın `_R`'sini kullandı). Abstract result alan adları **SEGW MPC property adlarıyla birebir** (UI parse'ı korumak için: ItemNumber/NetAmount/BpNumber/ProcessedCount...).

---

## 34. SAP-içi HTTP/OData servis çağrısı — KANONİK: ZBC002 iç gateway proxy (SM59 = legacy)

> **Senaryo:** ABAP'tan (RAP handler, klasik sınıf, FM…) released/standart bir OData servisini çağırmak
> (fiyat simülasyonu, BP API, vergi, dış API…). ZSD001 SimulatePricing (`API_SALES_ORDER_SIMULATION_SRV`),
> ZSD000 BP create (`API_BUSINESS_PARTNER`).

### ✅ KANONİK YÖNTEM (proje standardı, kullanıcı kuralı 2026-06-08) — canlı: ZSD001 + ZSD000

> **RFC-destination / SM59 kullanan TÜM SAP-içi OData API çağrıları bu mimariyle yapılır.**
> Aşağıdaki "Kural 0 / SM59" bölümü artık **ikincil/legacy** referanstır (yeni kodda kullanma).

**Neden SM59 değil:** SM59 host'u config'e taşır ama `sap-client` kodda hardcode kalır ('100') → QA/PRD client değişiminde kırılır. İç proxy host+client'ı runtime alır → **sistem & client bağımsız, kimliksiz**.

**Üç parça:**
1. **Paylaşılan `ZBC002_CL_GET_TOKEN`** (sahibi D_OSOZEN, BC paketi — ⛔ **DEĞİŞTİRME, sadece kullan**):
   - `get_host( iv_method, iv_token )` → `https://{host}:{port}/sap/opu/odata/sap/{iv_method}?sap-client={sy-mandt}` (host=`TH_GET_VIRT_HOST_DATA`, client=`sy-mandt`, runtime). `iv_token = abap_true` ise `&$top=1`.
   - `get_token( iv_method )` → iç proxy GET ile `x-csrf-token` döndürür.
2. **Motor:** `/iwfnd/cl_sutil_client_proxy=>get_instance( )->web_request( )` — SAP Gateway iç loopback. Harici HTTP / RFC-dest / kimlik YOK. **Singleton session** → token GET ile sonraki POST/PATCH CSRF'i paylaşır (ayrı `NEW zbc002` örnekleri sorun değil).
3. **POST/PATCH'i kendi paketinin altında** yaz (ZBC002'ye genel POST EKLENMEZ). Tam çalışan örnek: `ZQM012_CL_GET_TOKEN` (get_token + save_userdecision). `iv_method = '<SERVICE_SRV>/<Entity>'`.

```abap
" 1) CSRF
DATA(lo_api) = NEW zbc002_cl_get_token( ).
DATA(lv_csrf) = lo_api->get_token( iv_method = `API_X_SRV/A_Entity` ).
" 2) POST (PATCH için method='PATCH' + ( name = 'if-match' value = '*' ))
/iwfnd/cl_sutil_client_proxy=>get_instance( )->web_request(
  EXPORTING
    it_request_header = VALUE #(
      ( name = if_http_header_fields_sap=>request_method value = 'POST' )
      ( name = if_http_header_fields_sap=>request_uri    value = lo_api->get_host( iv_method = `API_X_SRV/A_Entity` ) )
      ( name = if_http_header_fields=>content_type        value = 'application/json' )
      ( name = if_http_header_fields=>accept              value = 'application/json' )
      ( name = 'x-csrf-token'                             value = lv_csrf ) )
    iv_request_body  = cl_abap_codepage=>convert_to( lv_payload_json )
  IMPORTING
    ev_status_code     = DATA(lv_status)
    et_response_header = DATA(lt_hdr)
    ev_response_body   = DATA(lv_body_x)
  EXCEPTIONS OTHERS = 4 ).
DATA(lv_response) = cl_abap_conv_codepage=>create_in( )->convert( lv_body_x ).
" sap-message header: VALUE #( lt_hdr[ name = 'sap-message' ]-value OPTIONAL )
```

**Tuzaklar (KANITLANDI):**
- **DİL (kritik):** `get_host` URL'e sadece `sap-client` koyar, `sap-language` KOYMAZ → UoM/text lookup gereken servis EN'de patlar (`S4 HTTP 400: Unit ... is not created in language EN`). Çözüm: request_uri'ye TR ekle → `value = |{ lo_api->get_host( iv_method = lc_method ) }&sap-language=TR|` (ZSD001 simulate).
- **Query'li URL (`?$filter`/`?$select`):** `get_host(iv_method)` sonuna `?sap-client` eklediği için **ham query'li path'i iv_method olarak VERME** (çift `?` olur). Bunun yerine host:port'u `get_host( `` )`'tan regex ile ayıkla, sonra `path + (query varsa & yoksa ?) + sap-client=sy-mandt` kur. Kanonik helper = ZSD000 `build_url`:
  ```abap
  DATA(lv_base) = NEW zbc002_cl_get_token( )->get_host( iv_method = `` ).
  DATA lv_hostport TYPE string.
  FIND REGEX `^(https?://[^/]+)` IN lv_base SUBMATCHES lv_hostport.
  DATA(lv_sep) = COND string( WHEN iv_path CS `?` THEN `&` ELSE `?` ).
  rv_url = |{ lv_hostport }{ iv_path }{ lv_sep }sap-client={ sy-mandt }|.
  ```
- **RAP behavior-handler:** proxy RAP context'inde **sorunsuz** (ZSD001 canlı). Eski `cl_http_client` comm-hatasında `MESSAGE`→`BEHAVIOR_ILLEGAL_STATEMENT` dump verirdi; proxy'de görülmedi.

**Uygulayan referans kod:** `ZSD001_CL_SO_MANAGER->simulate_pricing`; `ZSD000_CL_CUSTOMER_MAINTAIN` (`get_csrf_token` / `call_http_get` / `_post` / `_patch` / `build_url`).

---

## 34-LEGACY. SM59 destination yöntemi (İKİNCİL — yeni kodda kullanma, §34 kanonik tercih edilir)

> Tarihsel referans + SM59 ortamı zaten kuruluysa bilgisi. **Yeni API çağrısı = §34 kanonik (ZBC002 iç proxy).**

### Kural 0 — Kimlik kaynak koda YAZILMAZ (ADR 0005)
Legacy SEGW kodu sık sık `lo_client->authenticate( username = '...' password = '...' )` ile **parolayı koda gömer** (kopya tuzağı; güvenlik guard'ı da bloke eder). RAP kopyada **ASLA** taşıma. Çözüm: **SM59 destination** — kimlik/host/SSL **config'te (şifreli), source'ta değil.**

```abap
cl_http_client=>create_by_destination(
  EXPORTING destination = CONV rfcdest( 'Z<DEST>' )  " SM59'da tanımlı
  IMPORTING client = lo_client EXCEPTIONS OTHERS = 4 ).
```

### SM59 destination kurulumu — tuzaklar (her biri zaman kaybettirdi)
| # | Belirti | Kök neden | Çözüm |
|---|---|---|---|
| 1 | `Client connection to **http://**host**:443xx** broken` (connection test + runtime) | SSL kapalı → düz HTTP, HTTPS portuna (443xx) gidiyor | SM59 → Logon & Security → **SSL = Active** (RFCOPTIONS `s=Y`). SSL Client Cert = DFAULT/ANONYM |
| 2 | **401** (SSL düzeldikten sonra) | Logon kimlik göndermiyor (User/Pass boş; "Do Not Use a User" = kimliksiz; "current user" basic prompt-only) | **Basic Auth + SM59'da SAKLI teknik kullanıcı** (config, source değil) → en sağlam + RAP-safe. (Salt-okunur servis için teknik kullanıcı yeter, per-user şart değil) |
| 3 | **403 "/IWFND/MED/170 service 'sap' not found"** / 404 "segment 'sap'" | `create_by_destination` SM59 **Path Prefix'i HER ZAMAN** request URI'nin önüne ekler (prepend; `set_request_uri` de `~request_uri` header de). Kod tam OData path verirken prefix doluysa → çiftlenir | **SM59 Path Prefix'i BOŞ bırak** (destination = sadece host+SSL+logon). Kod tam path verir (`/sap/opu/odata/sap/<SRV>/<entity>`) → birebir gönderilir. (Erken "starts-with→as-is" varsayımı YANLIŞ çıktı; her zaman prepend.) |
| 4 | POST öncesi token | OData yazma CSRF ister | Önce **GET + `X-CSRF-Token: Fetch`** → token. Entity POST-only ise GET **404 verir ama token yine döner** (status'a bakma, ZSD001 gibi). Sonra POST + token |
| 5 | "current user (assertion ticket)" denemesi | Basis same-system assertion-trust ACL'i + RAP fazında ticket üretimi belirsiz | Gerçek per-user kimlik gerekmedikçe **kullanma**; basic+stored user daha öngörülebilir |

### ✅ KESİN SM59 DESTINATION SPEC (deneme-yanılma YAPMA — bu ayarlarla çalışır)
SM59 → HTTP Connection. Bu değerler **kanıtlandı** (ZSD001 SimulatePricing canlı, 2026-06-04):

| SM59 alanı | Değer | Not |
|---|---|---|
| Connection Type | **G** (HTTP to External Server) veya **H** (HTTP to ABAP System) | aynı-sistem self-call için H da olur |
| Target Host | `<sistemin kendi host'u>` | aynı sistem (self-call) |
| Service No (Port) | **44300** | HTTPS portu (4430 + instance 00) |
| Path Prefix | **BOŞ (empty)** | ⚠️ ZORUNLU boş — create_by_destination prefix'i prepend eder; kod tam path verir. Doluysa path çiftlenir (403 "service sap"). Boş = generic, tüm OData servisleri |
| **Logon & Security → SSL** | **Active** | ⚠️ ZORUNLU (HTTPS portu); kapalıysa "connection broken" |
| SSL Client Certificate | **DFAULT (SSL Client (Standard))** | yoksa ANONYM |
| **Logon & Security → Logon Procedure** | **SAP RFC Logon** | "Do Not Use a User" (kimliksiz→401) / "Basic Auth" / SSO DEĞİL. Target sistemde SAP RFC Logon izinli olmalı |
| User / Password / Lang / Client | **SM59'da SAKLI** (target sistemin SAP kullanıcısı) | kimlik **config'te (şifreli), source'ta DEĞİL** → ADR 0005 temiz |

> **AI YAPMAZ (ADR 0005-C):** destination yaratma/değiştirme = operatör/SM59. AI sadece `create_by_destination` ile **kullanır** ve bu spec'i operatöre verir.

### Reusability — bir destination kaç API'ye hizmet eder?
create_by_destination Path Prefix'i **her zaman** prepend ettiği için:
- **Path Prefix = BOŞ** + kod **tam path** verir (`/sap/opu/odata/sap/<SRV>/<entity>`) → **tek destination TÜM same-system OData API'lerine** hizmet eder (generic). **ÖNERİLEN.** Kanıt: ZSD001'de tek `ZLOCAL_ERP_HTTP` (boş prefix) hem `API_SALES_ORDER_SIMULATION_SRV` (simülasyon) hem `API_BUSINESS_PARTNER` (BP create) için çalışıyor.
- **Path Prefix = belirli servis** (`/sap/opu/odata/sap/API_X_SRV`) → o servise bağlı; kod sadece **göreli** kalanı vermeli (`/A_Entity`). Tam path verirsen çiftlenir → 403. Karışıklığı önlemek için **boş prefix + tam path** kullan.

### ⛔ EN KRİTİK: `MESSAGE` RAP handler'da YASAK → cl_http_client comm hatasında dump eder
`BEHAVIOR_ILLEGAL_STATEMENT · CL_HTTP_CLIENT · "Statement MESSAGE_E is not allowed"` — RAP behavior handler (transactional context) **`MESSAGE` statement'ını yasaklar**. `cl_http_client` **comm BAŞARISIZ olunca içeride MESSAGE verir** → dump.
- ✅ **Mutlu yol (200, hatta geçerli HTTP 4xx/5xx cevabı) → MESSAGE yok → sorun yok.** Sadece **transport/comm kopması** (SSL/logon/erişilemez) dump eder.
- → Bu yüzden destination **güvenilir bağlanmalı** (SSL+cred doğru). Comm hatasında düzgün hata yerine dump alırsın — kabul edilebilir uç durum ama bilinmeli.
- **Lokal `CALL FUNCTION` (RFC DESTINATION'sız) sorunsuz** (dış comm yok → MESSAGE yok). Bu yüzden RFC-tabanlı read (GetBalance) ilk seferde çalıştı, HTTP uğraştırdı.
- Klasik SEGW/DPC normal context'te koşar → orada MESSAGE/HTTP hatası dump etmez; **RAP daha katı.**

### Teşhis tekniği — RAP-dışı classrun probe (+ load-cache tuzağı)
Destination'ı handler'a gömmeden ÖNCE **`if_oo_adt_classrun` probe** ile test et — classrun **RAP BO context'i DIŞINDA** koşar → MESSAGE dump etmez, gerçek HTTP status/exception görünür. create_object.py (shell) + push_object.py (source) + `adt_classrun`.
- ⚠️ **classrun LOAD-CACHE tuzağı:** runtime yüklenen class'ı cache'ler → source'u düzenleyip tekrar koşunca **ESKİ çıktı** gelir (değişmez!). **Cache bust = YENİ class adı** (`Z..._PRB2`). Belirti: edit'e rağmen çıktı hiç değişmiyor.

### Servis adı kontrolü
Teknik servis (`API_..._SRV`) vs Gateway Z-alias (`ZAPI_..._SRV`) ayrı objelerdir. Hangisi aktif/yetkili: `/$metadata` → **200 vs 403/404**. ZSD001'de teknik ad 200, Z-alias 403 → teknik adı kullandık.

### Reçete (özet sıra)
1. SM59 destination: **SSL Active + Basic Auth stored user** (operatör/kullanıcı; ADR 0005-C → AI yaratmaz).
2. classrun probe (yeni-ad) ile destination'ı doğrula → 200 + csrf=VAR.
3. Manager'da `create_by_destination` + `set_request_uri( TAM path )` + GET(csrf)→POST. **Parola yok.**
4. Comm güvenilir → RAP handler'da çalışır (MESSAGE-dump sadece comm kopmasında).
5. Probe class'larını SİL (adt_delete), kaynak-kodda kimlik olmadığını doğrula.

---

## §34 — Source-based class TUZAĞI + RAP text node (\_Text) reçetesi + vague-scan bisect (2026-06-11, ZSD001 sipariş notları)

**A) `TYPE c LENGTH n` method-param tuzağı (ASIL patinaj sebebi):**
Source-based ABAP class'ta **METHOD parametresinde** `TYPE c LENGTH 100` → save reddedilir:
`OO_SOURCE_BASED / ExceptionResourceScanDuringSaveFailure` (HTTP 400, **satır no YOK**).
- İlginç: aynı `TYPE c LENGTH 220` TYPES/struct component'inde sorunsuz çalışır → sadece method imzasında kırar.
- **Çözüm:** method IMPORTING/EXPORTING'de `TYPE string` veya DDIC data element kullan, generic `c LENGTH n` KULLANMA.
- **Tek-ev:** method-imza save-scan ailesinin konsolide evi → [`adt-classes.md`](adt-classes.md) §24.6 (CURR DTEL / RANGE OF / built-in tip dahil).

**B) RAP unmanaged static-action handler'da sipariş başlık metni YAZMA — KRİTİK: PERSIST TUZAĞI:**
⚠️ **Bu senaryoda EML `CREATE BY \_Text` VE default `SAVE_TEXT` METNİ PERSIST ETMEZ** (2026-06-11 ZSD001, runtime kanıtlı):
- EML CREATE BY \_Text → buffer'da başarılı (`fc=0`, FAILED boş) AMA RAP controlled-commit released-BO save-sequence'i ayrı text-MODIFY'ı **commit etmez** → VA03/READ boş.
- `SAVE_TEXT` (default) → `subrc=0` AMA text-memory'yi COMMIT WORK ile flush eder; RAP commit bunu tetiklemez → yine persist YOK.
- **ÇÖZÜM: `SAVE_TEXT ... savemode_direct = 'X'`** (senkron direkt DB yazımı, COMMIT WORK bağımlılığı yok) → persist EDER. Doğal upsert (overwrite) + boş içerik=temizler.
```abap
" YAZMA (persist eden tek yol — savemode_direct ZORUNLU)
DATA: lt_lines TYPE TABLE OF tline, ls_header TYPE thead.
ls_header-tdobject = 'VBBK'. ls_header-tdname = iv_so. ls_header-tdspras = sy-langu.
APPEND VALUE tline( tdformat='*' tdline=iv_note1 ) TO lt_lines. ls_header-tdid = '0001'.
CALL FUNCTION 'SAVE_TEXT' EXPORTING header=ls_header savemode_direct='X' TABLES lines=lt_lines EXCEPTIONS OTHERS=1.
" OKUMA — EML READ BY \_Text (released, aynı VBBK store) sorunsuz çalışır:
READ ENTITIES OF i_salesordertp ENTITY SalesOrder BY \_Text
  ALL FIELDS WITH VALUE #( ( salesorder = iv_so ) ) RESULT DATA(lt_text). " ls_text-longtextid/longtext
```
ZSD001 text ID'leri: 0001/Z006/Z007, text object VBBK. **EML _Text recipe (FIELDS(longtext), key %target'ta, language verme) syntax olarak DOĞRU + entity `use update` destekler — AMA persist etmez bu akışta; okuma için EML, yazma için SAVE_TEXT savemode_direct.**
**PROCES DERSİ:** buffer-içi başarı (`fc=0`/`subrc=0`) ≠ PERSIST. **Read-back / VA03 ile gerçek kalıcılığı DOĞRULA.** Ayrıca: takılınca yaklaşım değiştirme (EML↔SAVE_TEXT bailout) — asıl sorun ORTOGONAL olabilir (burada COMMIT'ti); root-cause'u runtime diag (REPORTED+subrc mesaja) ile bul.

**C) Satırsız save-scan hatasında DOĞRU teşhis (patinajı engelleyen disiplin):**
`ResourceScanDuringSaveFailure` satır vermez → **feature suçlama/tahmin etme** (SAVE_TEXT yanlış suçlandı, saatler kayboldu).
1. Lokali **aktif SAP sürümüyle birebir** yap: `adt_get .../source/main` → diske yaz.
2. Push → **temiz baseline doğrula**.
3. Değişiklikleri **TEK TEK** ekle, her birinde push → kıran tam değişikliği bulursun.
4. push_object "Source uploaded"/"activated" **yanıltıcı olabilir** — `adt_get` aktif source ile **diff'leyerek** persist'i doğrula.
Detay: memory `feedback_source-based-class-type-c-trap-ve-vague-scan-bisect`.

**D) AKTİVASYON DOĞRULAMASI ZORUNLU (HTTP 200 KANIT DEĞİL) — wire et, not yetmez:**
Combined bdef+class activation `POST /sap/bc/adt/activation` **200 dönse bile aktive ETMEMİŞ olabilir** (2026-06-11: 200 ama `activationExecuted="false"` + `<chkl:messages type="E">` → metadata eski kaldı, saatler kayboldu). **Her activate sonrası MUTLAKA parse et:**
```python
ae   = re.search(r'activationExecuted="(\w+)"', r.text)        # "true" olmalı
errs = re.findall(r'type="E"[^>]*>.*?<txt>([^<]+)', r.text, re.S)  # boş olmalı
aktif = ae and ae.group(1)=="true" and not errs                # ikisi de değilse FAIL
```
Hazır helper: `create_rap_service.py::verify_active()`. **`severity="E"` aramak YETMEZ** — `<chkl:messages>` formatı + `activationExecuted` flag'ı şart. Function import beklerken son adım: metadata'da `<FunctionImport Name="X">` GERÇEKTEN var mı GET'le doğrula (republish sonrası). Bu kural [[feedback_done-tam-kapsam-dogrula]] + lessons PATTERN #4/#9'un aktivasyon-anı enforcement'ı.

---

## §35 — Mevcut belgeye partner/child EKLEME (CREATE BY \_assoc): `editableFieldFor` KEY alanı (2026-06-13, ZSD001 ZW/ZX ekleme)

**BELİRTİ:** Released BO'da (`I_SalesOrderTP`) **mevcut** siparişe `CREATE BY \_partner` ile partner eklenince partner **boş fonksiyonla** (`parvw=''`) oluşur → determination hatası **"Muhatap için muhatap rolünü girin"**. Yeni siparişte (deep-create) AYNI kod sorunsuz çalışır → kafa karıştırıcı.

**KÖK NEDEN (kanıt = projeksiyon CDS source):** `I_SalesOrderPartnerTP` projeksiyonunda:
```
key SalesOrderPartner.PartnerFunction,                  // KEY → create'te SALT-OKUNUR
    @ObjectModel.editableFieldFor: 'PartnerFunction'
    SalesOrderPartner.PartnerFunctionForEdit,           // create'te SET edilecek alan BU
```
Semantik key alanı (`PartnerFunction`) create'te yazılamaz; SAP, yazılabilir muadilini `<Key>ForEdit` olarak verir (`@ObjectModel.editableFieldFor`). Key'i set edersen **yok sayılır → alan boş kalır**.

**✅ ÇALIŞAN (mevcut belgeye partner ekleme):**
```abap
MODIFY ENTITIES OF i_salesordertp
  ENTITY salesorder CREATE BY \_partner FIELDS ( partnerfunctionforedit customer )
    WITH VALUE #( ( salesorder = iv_so
      %target = VALUE #( ( %cid = 'CZW' partnerfunctionforedit = 'ZW' customer = lv_kunnr_alpha )
                         ( %cid = 'CZX' partnerfunctionforedit = 'ZX' customer = lv_depo_alpha ) ) ) )
  ...
```
- `customer` ALPHA-pad'li (10 haneli) olmalı (pad'siz → boş partner, ayrı tuzak).
- Yeni sipariş deep-create'te (`%cid_ref` root'a) `partnerfunction` key'i DOĞRUDAN çalışır — sıfırdan kompozisyon ağacı key kabul eder. **Sadece mevcut belgeye EKLEME senaryosu `...ForEdit` ister.** create yolunu değiştirme.
- Önce mevcut VBPA partner fonksiyonlarını oku → route: varsa `UPDATE`, yoksa `CREATE BY \_assoc`, kaldırıldıysa `DELETE` (yoksa-UPDATE = `NOT_FOUND`).

**❌ DENENEN BAŞARISIZ (patinaj — saat kaybı):**
| Deneme | Sonuç |
|---|---|
| Var olmayan partneri `UPDATE` | `NOT_FOUND` (önce VBPA oku, route et) |
| `CREATE ... %target ( partnerfunction = 'ZW' ... )` | parvw BOŞ → "rol girin" (key yok sayıldı) |
| `FIELDS ( partnerfunction customer )` | aktivasyon: "PARTNERFUNCTION not a valid field" (key FIELDS'e konmaz) |
| Ayrı MODIFY → ana MODIFY'a taşıma (scope hipotezi) | **etkisiz** — sorun scope değil, alan-mapping'di (yanlış hipotez) |
| "Released-BO kısıtı, BAPI'ye geç" sonucu | **YANLIŞ** — kullanıcı reddetti; çözüm standart RAP'te vardı |

**🔑 PROCES DERSİ (takılmamak için):** `CREATE BY \_assoc` bir alanı **yok sayıyorsa / boş bırakıyorsa** → tahmin etme, scope/BAPI'ye kaçma. **ÖNCE projeksiyon CDS source'u oku** (`adt_get <Entity>TP cds include_source=true`) ve şunları ara: `@ObjectModel.editableFieldFor` (key'in yazılabilir muadili), `@ObjectModel.readonly`, suppress'li alanlar. Released BO'da yazılamayan key ≈ her zaman bir `...ForEdit` alanı vardır. Bu, [[feedback_playbook-once-oku]] + [[feedback_arastir-once-patinaj-uretim-gorev]]'in RAP-EML anıdır.

---

*Bu dosya her başarılı/başarısız RAP ADT işleminden sonra güncellenir (T1/T2). Pilot bitince retrospektif → ADR 0008 girdisi.*
