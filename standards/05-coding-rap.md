---
layer: L2
scope: project-wide
applies-to: backend
version: 1.0
last-updated: 2026-05-15
status: active
source: NTTDATA/TR ABAP Naming Guideline v1.0 (konsolide) + ADR 0005/0006 + ZSD001 ORDER pilotu
---

# RAP — RESTful Application Programming Standardı

## Stack: ABAP RAP (CDS view entity · BDEF · Behavior · Service Definition · Service Binding) → OData V2/V4

> **Konum:** Bu doküman `02-coding-backend.md` (klasik track: OData V2 **SEGW** · RFC/BAPI+CDS · Fiori Elements) ile **çatışmaz, onu tamamlar**. Bir WRICEF kalemi ya **klasik track** (02) ya **RAP track** (bu doküman) ile gider — ZSD001 için all-or-nothing (hafıza: `project_zsd001-ui-paradigm-all-or-nothing`). RAP seçilirse SEGW kullanılmaz.
>
> **Olgunluk:** RAP bu projede ORDER pilotuyla **KANITLANDI** (2026-06: ORDER FS/TS/KD + uygulama CANLI, çoklu-managed-root coexistence PASS, ZSD001 RAP PASS). Service binding **publish** yöntemi **doğrulandı** (AI-otonom publish çalışıyor). Operasyonel ADT REST pattern'i → L3 [`playbook/adt-rap.md`](../playbook/adt-rap.md).

---

## 1. ROLE & SCOPE

SAP S/4HANA 2025 on-premise, Clean Core **Level A** (RAP) hedefi. Bu standart: RAP obje modeli, katmanlama, naming (NTTDATA konsolide), BDEF kuralları, servis publish, ve **ADR 0005 yasaklarının RAP'a özel yüzeyi**.

---

## 2. NE ZAMAN RAP, NE ZAMAN KLASİK

| Senaryo | Track |
|---|---|
| Yeni Z transactional doküman (Z tablo, std doküman/BAPI sarmıyor) | **RAP managed** |
| Std doküman (VBAK/LIKP vb.) üzerine create/update | **RAP unmanaged** (released BAPI/EML) veya klasik DPC_EXT — std tabloya DİREKT yazma yasak (ADR 0005 B) |
| Salt-okunur liste/worklist/value help (büyük veri, pushdown) | **Salt-okunur query CDS** (RAP servisinde davranışsız expose) |
| Klasik dialog/rapor, mevcut SEGW servisi | **Klasik track (02)** — dokunma, RAP'a zorla taşıma yok |

> Karar gerekçesi her zaman yazılır (Clean Core Level A/B/C/D notu — `01-naming.md` §5).

---

## 3. RAP OBJE MODELİ & KATMANLAMA (zorunlu)

```
Service Binding  (UI/API, _O2/_O4)        ← publish (AI-otonom olmalı; operatör=0)
  └ Service Definition (UI/API)            ← expose listesi
      ├ Projection view  ZSDxxx_C_*  (+ behavior projection)   ← consumption layer
      └ Interface view   ZSDxxx_I_*  (root) composition of child ← interface layer
          └ Behavior Definition (= root entity adı)            ← managed/unmanaged
          └ Z tablo(lar)  ZSDxxx_T_*                            ← persistence (SADECE Z)
```

**Katman kuralı:** Projeksiyon doğrudan tabloya bakmaz; interface view'a bakar. Interface view sadece Z tablo(lar)a bakar. Transactional BO'nun persistence'ı **yalnızca Z tablo** (ADR 0005 A/B).

---

## 4. NAMING (NTTDATA konsolide — `01-naming.md` otorite)

RAP naming **icat edilmez**; `01-naming.md` (NTTDATA Guideline) §4.2/§4.4.1/§4.4.3/§4.4.5 otoritedir. RAP'a indirgenmiş net tablo (`<PKG#>` = paket no, ör. `SD001`):

| RAP Objesi | Prefix | ZSD001 Örnek | Kaynak |
|---|---|---|---|
| Interface (root) view | `I` | `ZSD001_I_ORDER` | §4.4.1 Interface View |
| Interface child view | `I` | `ZSD001_I_ORDERDEST` | §4.4.1 |
| Projection (consumption) view | `C` | `ZSD001_C_ORDER` | §4.4.1 Projection View |
| Root view (ayrık gerekirse) | `R` | `ZSD001_R_ORDER` | §4.4.1 Root View |
| Extension view | `E` | `ZSD001_E_ORDER` | §4.4.1 |
| **Behavior Definition** | **= root entity adı** | `ZSD001_I_ORDER` | SAP zorunlu: BDEF adı = root CDS adı |
| Behavior impl. sınıfı | `ZCL_<PKG#>_` | `ZCL_SD001_ORDER` | §4.4.3 Class (`ZBP_*` KULLANILMAZ — proje `ZCL_SD001_*` regex'i) |
| Service Definition | `UI` / `API` | `ZSD001_UI_ORDER` (UI) / `ZSD001_API_ORDER` (entegrasyon) | §4.2 |
| Service Binding | `UI`/`API` + **`_O2`/`_O4`** | `ZSD001_UI_ORDER_O2` (V2), `ZSD001_UI_ORDER_O4` (V4 hedge) | §4.2 — OData versiyon suffix zorunlu |
| Data Element (RAP'ın ürettiği) | `E` | `ZSD001_E_VOYNO` | §4.4.5 — **`DE` DEĞİL** |
| Domain | `D` | `ZSD001_D_VOYNO` | §4.4.5 — **`DOM` DEĞİL** |
| Draft DB tablo (draft'lı senaryoda) | `A` … `_D` | `ZSD001_A_ORDER_D` | §4.4.5 |

> **Class naming — TEK desen (karar 2026-06-09, kullanıcı).** Sınıfın rolü ne olursa olsun (RAP behavior impl. **veya** iş mantığı/utility) **`ZCL_<PKG#>_<ad>`** kullanılır (NTT §4.4.3 kanonik): `ZCL_SD001_ORDER` (behavior), `ZCL_SD001_SO_MANAGER` (iş mantığı). **`ZSD<NNN>_CL_*` deseni LEGACY** — yeni sınıfta KULLANILMAZ (eskiden L4 .rules.md'de "iş mantığı class" olarak vardı; L2 NTT ile çelişiyordu, geri hizalandı). `ZBP_*` da kullanılmaz. Mevcut `ZSD<NNN>_CL_*` objelerin rename'i ERTELENDİ → [`governance/deferred-triggers.md`](../governance/deferred-triggers.md).

### 4.1 `ZSD001_I_*` Namespace Çakışması — ÇÖZÜM

`01-naming.md` `I` prefix'ini hem **Include** (§4.1, PROG/I) hem **Interface View** (§4.4.1, DDLS) için verir. Bu **bilinçli paylaşımlı namespace**'tir; disambiguation **obje tipi + klasör** ile:

| `ZSD001_I_*` | Obje tipi | Klasör | Uzantı |
|---|---|---|---|
| Klasik program include | PROG/I | `programs/` | `.abap` |
| RAP interface view | DDLS view entity | `cds/` | `.cds` |

Validator (`check_package_naming.py`) klasör bazlı doğrular → çakışma **enforcement'ta yok**. Regex `^ZSD001_I_[A-Z0-9_]+$` ikisini de kapsar. Kural: aynı kök adı iki tip için kullanma (ör. `ZSD001_I_ORDER` include + view aynı anda olmaz).

### 4.2 BDEF adı kuralı

SAP, Behavior Definition'ın adının **root view entity ile aynı** olmasını zorunlu kılar. Yani BDEF objesi de `ZSD001_I_ORDER`. Behavior **implementation sınıfı** ayrıdır: `ZCL_SD001_ORDER`.

---

## 5. BEHAVIOR DEFINITION KURALLARI

| Konu | Kural |
|---|---|
| Implementation type | Z tablo + std sarmıyorsa **managed**. Std doküman sarıyorsa **unmanaged** (released BAPI/EML; std tabloya direkt EML yazma = ADR 0005 B ihlali). |
| Draft | Varsayılan **draft'sız** (pilot kararı). Draft gerekirse ayrı değerlendirilir; draft DB tablo `ZSDxxx_A_*_D`. |
| Numbering | Managed early/late numbering; NR objesi **kullanıcı tarafından** sağlanır/yaratılır (ADR 0005 C — AI NR yaratmaz). BDEF `numbering : managed;` veya determination'da NR FM. |
| Actions | Factory/instance action camelCase: `copyWithReference`. İş mantığı behavior sınıfında. |
| Lock | Managed framework optimistic (ETag) + mevcut `EZSD001_*` lock objesi. Elle enqueue kurulmaz. |
| **VA02-tarzı belge kilidi** | "Açarken kilitle / başkası düzenliyorsa salt-okunur" gerekiyorsa (freestyle/V2, draft'sız) → **ortak app-level kilit** `ZSD000_CL_APP_LOCK` + `ZSD000_T_LOCK` (Acquire/Release static-action, UI heartbeat/beforeunload/5dk timeout). Gerçek belge (VA02 de açar) → ek **ENQUEUE_READ**. **Reçete: [`playbook/howto-document-lock.md`](../playbook/howto-document-lock.md)** · karar/alternatifler (draft): **ADR 0014**. |
| **Lock + ETag (BLOCKER)** | ⛔ Yazma operasyonlu (create/update/delete) **managed** BDEF root'unda **`lock master`** + **`etag master <LastChangedField>`** ZORUNLU. ETag-master alanı CDS root view'da `@Semantics.systemDateTime.lastChangedAt: true` olmalı (+ `createdAt/createdBy/lastChangedBy` admin alanları §9A). Child: `lock dependent by _assoc` + `etag dependent`. **Eksikse managed RAP concurrency'de çalışmaz** (gap-analysis #16 anekdotu). Reviewer: `check_rap_managed_etag.py` (`rap_bdef_creation`). |
| Validation/Determination | Zorunlu alan, kod doğrulama → validation; default/türetilmiş → determination. `BAPIRET2` mesaj deseni (playbook §30). |
| EML | Tek `MODIFY ENTITIES` bloğu, tüm `DATA` metod başında, `%cid` unique, `COMMIT ENTITIES` Gateway context'inde yapma (playbook §29 kuralları RAP'ta da geçerli). |
| **READ ENTITIES BY \_assoc — keys-only tuzağı (HIGH)** | ⚠️ `READ ENTITIES ... ENTITY parent BY \_child FROM <key> RESULT lt` child'ın **YALNIZ KEY alanlarını** doldurur; non-key (tarih/durum/tip/tutar) INITIAL kalır → validation/determination **sessizce yanlış** (syntax 0-error, ATC temiz, aktive olur → **yalnız RUNTIME'da çıkar**). Non-key okuyacaksan **`ALL FIELDS WITH <key>`** (tüm alan) veya **`FIELDS ( f1 f2 ) WITH <key>`** (seçili — `FROM` DEĞİL `WITH`) ŞART. Yalnız existence/key kontrolü (line_exists) gerekiyorsa `FROM` yeterli. **ZSD001 = doğru referans (`ALL FIELDS WITH`)**. Reviewer: `check_rap_byassoc_keys_only.py`. Checklist: BE-20 · memory `feedback_rap-by-assoc-read-all-fields`. |

---

## 6. ⛔ ADR 0005 — RAP'A ÖZEL YASAK YÜZEYİ (bypass yok)

| ADR 0005 | RAP'taki tezahürü |
|---|---|
| **A** Std obje koruma | Interface/projection view **sadece Z tablo/Z CDS** kaynaklı. Std CDS/BO append/extend etme. Std behavior'a `extension` yazma yasak. |
| **B** Std tablo direkt I/U/D | Behavior EML'i (managed) **sadece Z tablo**a yazar. Std doküman gerekiyorsa unmanaged + **released BAPI/RFC** (sıra: BAPI→RFC FM→BDC→manuel). Std tabloya `MODIFY ENTITIES`/SQL = YASAK. |
| **C** Sistem state | Transport/package **yaratma yok**. BDEF/CDS/SD/SB hep kullanıcının verdiği aktif TR'ye. Service binding publish bir **transport** kullanır, yenisini yaratmaz. |
| **D** Z text TR + tam | CDS `@EndUserText.label`, BDEF `@EndUserText`, SD başlığı **TR ve tam**; **tahmin edilmez** — <LEGACY_SOURCE> SEVKEMRI/TD spec'ten (hafıza: `feedback_zli-obje-text-tahmin-yasak`). Text, aktivasyon doğrulama readback'inde teyit edilir (mekanizma **tek-ev → §9**). |

**Field adları** `ZSDxxx_T_*` tablolarından **DDIC'ten okunur, tahmin edilmez** (hafıza: `feedback_<legacy_source>-field-adlari-sistem-bagimli`).

---

## 7. SERVICE DEFINITION / BINDING / PUBLISH

| Konu | Kural |
|---|---|
| Service Definition | `UI` (Fiori/SADL UI) veya `API` (entegrasyon). `expose` listesi: projection view(ler) + salt-okunur query CDS. Interface view doğrudan expose edilmez (consumption layer üzerinden). |
| Service Binding | Tip: **OData V2 - UI** birincil (`_O2`). **Hedge:** aynı SD'ye **OData V4 - UI** binding (`_O4`) — yarat+publish, kullanma; backend-rewrite'sız gelecek kapısı (≈sıfır maliyet). |
| **Publish** | **AI-otonom (operatör = 0).** Bu, RAP'ı SEGW yerine seçmenin TÜM gerekçesidir. Yöntem L3 playbook'ta; **ORDER pilotunda KANITLANDI (2026-06, otonom publish CANLI).** |
| Doğrulama | Publish sonrası servis URI **canlı** GET 200 ile doğrulanır; `$metadata` çekilir. |

---

## 8. GÜVENLİK

- Her interface/projection view: `@AccessControl.authorizationCheck: #NOT_REQUIRED` veya `#CHECK` (zorunlu annotation). Yetki gerekiyorsa DCL (`@AccessControl` + access control objesi).
- Service binding publish ≠ FLP/IAM exposure. Prod tile/katalog (IAM/BC/BR) kapsam dışıdır (pilot dev-proxy).

---

## 9. SÜRÜM & DEĞİŞİKLİK

- **Aktivasyon doğrulama (tek-ev):** RAP objesi aktif sürümü her zaman REST GET ile doğrulanır (`adtcore:version="active"`). §6-D'deki TR-text doğrulaması da bu readback üzerinde yapılır (ayrı bir GET değil).
- **Persist ≠ buffer:** RAP/EML yazımında buffer-başarısı (`fc=0`/`subrc=0`/HTTP-200) kalıcılık KANITI DEĞİL → read-back ile gerçek persist doğrula (hafıza: `feedback_done-tam-kapsam-dogrula`). ADT-spesifik doğrulama matrisi (CDS=version=active · RAP-text=read-back/VA03 · activate=activationExecuted · push=adt_get-diff) → [`../playbook/adt-rap.md`](../playbook/adt-rap.md) §34-D. Gate: `check_sap_active_version` + `check_source_drift`.
- **Method-imza save-scan tuzakları** (CURR DTEL / `RANGE OF ZZ1_*` / built-in `TYPE F/P/C LENGTH n` method imzasında → `ExceptionResourceScanDuringSaveFailure`): kanonik reçete → [`../playbook/adt-classes.md`](../playbook/adt-classes.md) §24.6. Gate: `check_method_param_type_c` + `check_abaplint`.
- Yeni RAP pattern başarılı/başarısız → L3 `playbook/adt-rap.md` (T1/T2). Bu doküman sadece **stabil kural** değişince güncellenir (semver).

---

## 9A. AUDIT ALANLARI AUTO-FILL (ZORUNLU)

> Bağlayıcı. Pattern/gotcha: [`../playbook/ui-backend-rap.md`](../playbook/ui-backend-rap.md) §F.

Tabloda `created_by/create_date/create_time/updated_by/update_date/
update_time` (veya muadili) audit alanları varsa **AI otomatik doldurur**
— kullanıcı ayrıca istemese bile. Her yeni programda:

1. DDIC'ten audit alanlarını tespit et; operatöre **kural teyidi**.
2. Varsayılan: **create → created_* VE updated_*; sonraki update →
   SADECE updated_*; created_* asla değişmez.**
3. Mekanizma: **idempotent `setAdmin` determination** (`on save
   { create; update; }` root+child; instance-guard cyclical-dump'ı
   önler; `IN LOCAL MODE`). Guard'sız det = dump; `with additional
   save` + early numbering = create component boş → KULLANMA.
4. Edm.Time → UI `sap.ui.model.odata.type.Time`, export `EdmType.Time`.

---

## 9B. ORTAK VALUE-HELP CDS (ZORUNLU, ADR 0009)

> Bağlayıcı. Politika: [`../governance/decisions/0009-ortak-value-help-cds-politikasi.md`](../governance/decisions/0009-ortak-value-help-cds-politikasi.md).

Generic master/org verisi (but000, tvkot, tvknt, t001...) üzerindeki,
app-mantığı içermeyen value-help CDS'leri **ortak `ZSD000_CLC`** paketinde
`ZSD000_I_*` olarak **tek sefer** yaratılır; tüketen RAP servisi SRVD'de
`expose` + association ile kullanır (kopyalama YOK). App'e özel / Z-tablo
VH'si ilgili pakette local kalır.

**Her geliştirmede zorunlu:** VH envanteri çıkarılır; her aday için
"ortak `ZSD000_I_*` / paket-local" önerisi **kullanıcıya sorulur**, yerleşim
kullanıcı onayıyla netleşir. AI tek başına karar vermez (ADR 0005: paket/TR
yaratmaz). Mevcut `ZSD000_I_*` varsa yeniden yaratılmaz.

**İLKE — generic BP VH/ad-çözümü YASAK (BPNAME anti-pattern, 2026-06-17 sweep):**
Bir partner alanının değeri **DAİMA ya CUSTOMER (KNA1/KUNNR) ya VENDOR (LFA1/LIFNR)**'dur
— generic BusinessPartner (but000/BU_PARTNER) arama-yardımı **veya** ad-çözümü
(join/assoc) YARATMA. Her partner alanını customer/vendor sınıflandır:
- **CUSTOMER** → picker `ZSD000_I_CUSTOMER_VH` (knvv, key Kunnr) ya da partner-fonksiyonu
  spesifik `ZSD000_I_CUSTOMER_WE/ZW/EC_VH` (knvp, key Kunn2); ad-çözümü released **`I_Customer`** (Customer/CustomerName).
- **VENDOR** → picker `ZSD000_I_VENDOR_VH` (I_Supplier, key Lifnr); ad-çözümü released **`I_Supplier`** (Supplier/SupplierName).
Gerekçe: BU_PARTNER ≠ KUNNR/LIFNR (CVI) → generic BP-join sessizce **boş/yanlış ad** döndürür.
Bug-checklist: `BE-19`. (Tarihsel `ZSD000_I_BPNAME` 2026-06-17 silindi.)

---

## 9X. CLEAN CORE — released-object + aile matrisi (dual-track on-prem)

> Biz **dual-track on-prem**'iz (RAP + bilinçli klasik). Clean Core ailelerinin **hepsi bize uygulanmaz**. SAP'nin kendi rehberi: *ABAP Language Version / Allowed Object Types ATC check'leri classic ABAP için **hariç***. Tam matris + gerekçe: [`../governance/research/sap-ai-tooling-comparison.md`](../governance/research/sap-ai-tooling-comparison.md).

- **Tablo→released CDS:** yeni RAP CDS'te std tablo (MARA/VBAP/LIPS...) yerine released CDS (I_Product/I_SalesOrderItem...) **tercih et**. Pre-flight: `check_released_objects.py` (WARNING, reviewer cds/rap zincirinde) → successor önerir. Hard kural değil (ADR 0005-B READ'i yasaklamaz); Clean Core Level A tercihi.
- **Tüm-tip released-API** (class/IF/FM): OTORİTE = SAP yerel **ATC "Usage of APIs"** (`adt_atc_check`, S/4 2025+PCE). Regex'le taklit edilmez.
- **ALINMAYAN aileler (bilinçli):** ABAP-Cloud dil-kapsamı / no-classic-construct (CALL SCREEN/SUBMIT/CALL TRANSACTION/FORM-PERFORM/dynpro) — klasik track'imizi (ADR 0012 Dynpro/ALV) yanlış flag'ler; SAP de klasik için hariç tutuyor.
- **Zaten kapsanan:** std-obje değiştirme yok (ADR 0005) · `view entity`+`sqlViewName` yok (checklist C-RAP-VE-02).
- **CDS perf (secondsky cross-check):** `@AbapCatalog.compiler.compareFilter: true` · eager join yerine **association (join-on-demand)** · post-aggregation filtre için `HAVING`.

---

## 10. İLGİLİ

- [`01-naming.md`](01-naming.md) — NTTDATA naming otorite (RAP naming buradan türer)
- [`02-coding-backend.md`](02-coding-backend.md) — klasik track (SEGW/FE) — RAP'ın alternatifi
- [`../playbook/adt-rap.md`](../playbook/adt-rap.md) — L3 RAP ADT REST pattern bankası
- [`../playbook/checklists/rap-creation.md`](../playbook/checklists/rap-creation.md) — reviewer checklist
- [`../playbook/checklists/rap-troubleshoot.md`](../playbook/checklists/rap-troubleshoot.md) — hata teşhisi + BOTD unit-test + ATC no-suppress
- [`../ERP/SD/ZSD001_CLC/.rules.md`](../ERP/SD/ZSD001_CLC/.rules.md) — L4 paket naming (RAP satırları)
- ADR [`0005`](../governance/decisions/0005-sap-standart-obje-koruma-ve-sistem-state-yasaklari.md) · [`0006`](../governance/decisions/0006-reviewer-agent-pattern.md)
