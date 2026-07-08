---
applies_to: [s4_private]
layer: L3
scope: project-wide
type: pattern-bank
applies-to: ui-backend-rap
last-updated: 2026-05-15
source: ORDER (ZSD001) RAP backend — ilk yayından kapanışa kadar yaşanan
        TÜM backend patinajları (CDS/BDEF/behavior/SRVD/publish/tooling)
canonical-detail: adt-rap.md §32 (bu dosya = "neyle takıldık + baştan
        nasıl önlenir" merceği; kanonik implementasyon adt-rap.md'de)
---

# UI Uygulaması RAP Backend — Operasyonel Tecrübe Bankası

> **Bu dosya neden ayrı?** [`ui-freestyle-odata-v2.md`](ui-freestyle-odata-v2.md)
> tarayıcı tarafıdır. Bu dosya bir freestyle UI'ı **besleyen RAP backend**
> (CDS view entity, BDEF, behavior class, SRVD/SRVB, publish, MCP/script
> tooling) tarafında ORDER'de yaşanan patinajların damıtımıdır.
> **Kanonik implementasyon detayı** [`adt-rap.md`](adt-rap.md) §32'dedir
> (tek doğru kaynak); burada **semptom→kök→çözüm→önleyici** merceği +
> §0 PRE-FLIGHT var. `[proje-özel]` işaretliler hariç tümü RAP backend'lerde ortak.

---

## §0 YENİ PROGRAM RAP BACKEND — PRE-FLIGHT (patinaj önleyici)

UI'ın CDS/BDEF/behavior'ını kurmadan önce:

1. **Aktivasyon sırası ezberle:** interface CDS → projection CDS → BDEF
   (interface+projection) → behavior class → SRVD → (kullanıcı) SRVB
   Unpublish→Publish. CDS değişince ÜSTÜndeki BDEF **re-activation** ister.
2. **Brand-new CDS** = MCP `adt_push_source` ilk yaratımda **lock-cache bug**
   (deterministik, retry=patinaj). Yeni DDLS'i `populate_cds_views.py
   --only <NAME> --force-recreate` (bağımsız lock) ile yarat → `adt_activate`.
   MEVCUT obje update'inde MCP push normal çalışır.
3. **Numbering** (NR object, CHAR key): BDEF'e `early numbering` keyword'ü
   + CCIMP `earlynumbering_create FOR NUMBERING` + `NUMBER_GET_NEXT`.
   **determination DEĞİL** (key-set determination = DETVAL dump).
   `numbering : managed` SADECE UUID — CHAR key ile kullanma.
4. **Projeksiyon view kısıtı:** `cast/coalesce`/ifade projeksiyonda
   DESTEKLENMEZ → ifadeyi **interface** view'a koy, projeksiyon düz expose.
   Aggregation (count) root transactional view'da OLMAZ → ayrı agregasyon
   helper view + association ile expose.
5. **Calculated/assoc CDS alanı** BDEF'te `field(readonly)` ile bildirme
   (gereksiz; otomatik read-only). Composition child KEY alanı →
   `field ( readonly : update )` (B.4 + "key field readonly" uyarısı kapanır).
6. **det/val izolasyon disiplini:** önce SAF CRUD → e2e YEŞİL → det/val'i
   TEK TEK izole geri ekle (çalışan CRUD ≠ çalışan det/val).
7. **e2e doğrula:** deep-create JSON POST (`{...h, to_Child:{results:[…]}}`)
   → 201 + numara atandı + validasyon çalıştı kanıtı. Kullanıcıya re-publish
   yaptırmadan UI testine geçme.
8. **ADR 0005:** Z obje masterLanguage **TR** (MCP post_shell EN yaratır →
   raw REST + TR shell + post-create doğrula). SAP-yazma öncesi
   `run_review.py` (MCP reviewer_timeout → `skip_reviewer` + manuel run).
9. **Value-help envanteri (ADR 0009):** Tüm VH adaylarını listele; her
   biri için **ortak `ZSD000_I_*` / paket-local** önerini çıkar ve
   **KULLANICIYA SOR**. Generic master/org (but000/tvkot/tvknt/t001...)
   = ortak ZSD000_CLC, tek sefer; mevcut varsa yeniden yaratma → SRVD
   `expose` + assoc. App-özel/Z-tablo VH = local. AI tek başına karar
   vermez, paket/TR yaratmaz.

---

## §A CDS (view entity)

| # | Semptom | Kök neden | Çözüm | Kapsam |
|---|---|---|---|---|
| A1 | Aktivasyon: `Field X contains a not supported expression` | `cast/coalesce`/ifade **projeksiyon** view'da | İfadeyi **interface** view'a taşı; projeksiyon düz expose (çalışan assoc-name pattern'i gibi) | all |
| A2 | Booking/satır SAYISI gibi agregasyon gerekiyor ama root transactional | RAP root view 1:1 olmalı; `group by`/`count` root'u bozar | Ayrı **agregasyon helper view** (`count … group by`) + root'tan `association` → projeksiyonda `coalesce(_H.Cnt,0)` (interface'te) | all |
| A3 | Türetilmiş tarih/alan (ör. demuraj+free) | Klasik CDS `cast(case when … dats_add_days(…) end as abap.dats)` | Interface view'da computed element; projeksiyon expose; BDEF'te bildirme (otomatik read-only) | all |
| A4 | Value-help view aktive olmuyor "HTTP 400 pre-audit" | **Ortamsal/geçici** olabilir (ORDER'de VKORGVH böyleydi) | Hemen DROP etme; gerçek hatayı al, tek temiz deneme yap (genelde düz aktive olur) | all |

## §B BDEF + behavior

| # | Semptom | Kök neden | Çözüm | Kapsam |
|---|---|---|---|---|
| **B1** | `The operation "CREATE" is not activated for entity "X"` (CCIMP earlynumbering satırını gösterir, yanıltıcı) | BDEF'te **`early numbering` keyword'ü eksik** | Root behavior characteristic'e `early numbering` ekle (lock/authorization'dan sonra, `{` öncesi) | all (NR'li) |
| B2 | `BEHAVIOR_CONTRACT_VIOLATION CC/C:EMPTY_UPDATE` | determination KEY alanını `MODIFY..UPDATE` etmiş | Key asla determination-UPDATE; numara = `earlynumbering_create FOR NUMBERING` (`NUMBER_GET_NEXT`) | all |
| B3 | `numbering : managed` ile CHAR key uyumsuz | managed-numbering sadece UUID/RAW16 | NR-objesi CHAR key → managed-numbering KULLANMA; early numbering handler | all |
| B4 | `RAISE_SHORTDUMP / LCX_ABAP_BEHV_DETVAL_ERROR` (jenerik) | det/val handler runtime patladı | **İzolasyon:** BDEF saf CRUD'a indir → e2e yeşil → det/val TEK TEK, her biri ayrı aktive+test ile geri ekle | all |
| B5 | "key field DESTINATIONPORT should be flagged readonly" uyarısı + composition child key UI'da değişebiliyor | Child key alanı için kısıt yok | `field ( readonly : update ) <ChildKey>` (B.4 server-enforce + uyarı kapanır) | all (composition child key olan) |
| B6 | `authorization master ( global )` → W/E | `get_global_authorizations` handler yok | Boş gövdeli `get_global_authorizations` ZORUNLU (permissive) | all |

## §C Aktivasyon sırası / circular

| # | Semptom | Kök neden | Çözüm | Kapsam |
|---|---|---|---|---|
| C1 | CDS değişti, BDEF/class aktivasyonu "CREATE not activated" / inconsistent | CDS değişince üstündeki BDEF re-activation ister; class aktif-değil create'i görür (circular) | **Staged:** önce interface+projection BDEF'i tek aktive (create aktif olsun) → sonra class. Veya pbactivate (bdef+bdef+class birlikte) | all |
| C2 | Projeksiyon "inconsistent in active version" zinciri | Bağımlı obje bozuk inactive kaldı | Bağımlı CDS'i temiz kaynakla push → graph activation ikisini birlikte aktive eder | all |
| C3 | Aktivasyon "cancelled" tek E yüzünden | Mass activation set'inde 1 hata tüm seti iptal eder | Hatasız alt-küme önce (örn. sadece BDEF), sonra kalan | all |

## §D SRVD / SRVB / publish

| # | Konu | Kural | Kapsam |
|---|---|---|---|
| D1 | Yeni alan (mevcut expose'lu entity'de — BookingCount/SalesOrgName) | SRVD kaynak DEĞİŞMEZ; kullanıcı **tek** Eclipse SRVB Unpublish→Publish → `$metadata`'da otomatik çıkar | all |
| D2 | Yeni entity (value-help view — VKORGVH) | SRVD'ye `expose` ekle + aktive et + kullanıcı re-publish | all |
| D3 | Doğrulama | Re-publish sonrası canlı `$metadata` GET → yeni alan/entity VAR mı deterministik kontrol (UI testine göndermeden) | all |

## §E Tooling (MCP / script)

| # | Semptom | Kök neden | Çözüm | Kapsam |
|---|---|---|---|---|
| **E1** | Brand-new DDLS `adt_push_source` → `[423] InvalidLockHandle`, "SAP did not return CORRNR", her çağrı AYNI handle (deterministik) | MCP server ilk yaratımda stale lock handle cache'liyor | **Retry=patinaj.** `populate_cds_views.py --package … --source-dir … --only <NAME> --force-recreate` → `mcp adt_activate <NAME> ddls`. MEVCUT obje update'inde bug YOK | all |
| E2 | `adt_post_shell`/`adt_get`/`adt_activate` bazı tip desteklemiyor (DDLS/bdef) | MCP tool kapsamı sınırlı | bdef = `create_rap_service.py --step bdef/ccimp/pbactivate`; ddls activate = MCP `adt_activate` (destekler) | all |
| E3 | MCP reviewer timeout | MCP wrapper'da bilinen sorun | `skip_reviewer=true` + manuel `python scripts/validators/run_review.py --task rap_cds_creation` (ADR 0006 yine zorunlu) | all |
| E4 | Z obje EN dilde yaratıldı | MCP post_shell EN | raw REST + `masterLanguage=TR` shell + post-create `adt_get include_source=false` doğrula | all (ADR 0005 D) |

## §F Audit alanlari auto-fill — STANDART (KANITLANDI 2026-05-19)

> **ZORUNLU & otomatik:** Her RAP backend'inde, tabloda created/updated
> by-date-time (veya benzeri) audit alanlari varsa AI bunlari otomatik
> doldurur. Her geliştirmede: DDIC'ten audit alanlarini tespit et +
> operatöre **kural teyidi** (varsayilan: **create → created_* VE
> updated_*; sonraki update → SADECE updated_*; created_* korunur**).

**ÇALIŞAN YÖNTEM — idempotent `setAdmin` determination:**
- BDEF root+child: `determination setAdmin on save { create; update; }`
  (RAP: `{ update; }` tek başına YASAK — "update only with create").
- Handler (her entity için ayri lhc): `READ ENTITIES ... FIELDS (CreatedBy)`
  → `CreatedBy` BOŞ ise yeni → 6 alan; dolu ise → updated_* (3 alan).
  `MODIFY ENTITIES IN LOCAL MODE ... UPDATE FROM lt_upd` (`%control` ile).
- **İDEMPOTENT GUARD (kritik):** instance `DATA mt_done` (LUW-scope,
  stateless OData) — işlenen anahtar 2. pas'ta `CONTINUE` → MODIFY yok
  → on-save det re-trigger zinciri **kırılır**. Guard'siz hali =
  `RAISE_SHORTDUMP LCX_ABAP_BEHV_DETVAL_ERROR "Infinite loop caused by
  cyclical triggering of on-save determinations"`.

**DENENEN VE BAŞARISIZ:**
- Ayrı `setCreateAdmin{create}` / `setUpdateAdmin{update}` → RAP
  "update yalnız create ile" → reddedilir.
- Guard'sız tek `setAdmin` (IN LOCAL MODE olsa bile) → cyclical dump.
- `with additional save` saver → dump yok ama early-numbering'de
  `create-voyage` component'i BOŞ (create admin yazılmaz; `%key`
  fallback de tutmaz). update yolu çalışır, create çalışmaz.

**Edm.Time gösterim/export:** TIMS alani OData Edm.Time → ham `{Field}`
`PT0H0M0S` (ISO duration) gösterir. UI `sap.ui.model.odata.type.Time`,
export `EdmType.Time` (kanonik personalizer kind `'time'`).

## §H Salt-okunur RAP rapor backend'i (wrapper view + DCL + SRVD/SRVB) — KANITLANDI 2026-06-08 (ZSD001/005/006)

Klasik bir ALV raporunu (mevcut DDIC-tabanlı CDS view'ı olan) RAP+grid'e taşırken, **transactional BDEF/behavior'a GEREK YOK** — salt-okunur query servisi yeterli:

1. **Wrapper view entity:** `define view entity ZSD0NN_C_<X> as select from <klasik_DDL_view> { key <belge> as ..., key <kalem> as ..., ... }` — mevcut klasik CDS'i **SAR** (logic/join yeniden yazma; klasiğe DOKUNMA). `@AccessControl.authorizationCheck: #CHECK`, CamelCase alias, key alanlar başta, `@Semantics` (qty/amount) **wrapper'da tekrar** (kaynak `@Metadata.ignorePropagatedAnnotations` ise). Tüm alanları 1:1 expose.
2. **DCL** (`ZSD0NN_C_<X>`): `grant select where ( SalesOrganization ) = aspect pfcg_auth( V_VBAK_VKO, VKORG, ACTVT = '03' )` (klasik `sd_authority_check` karşılığı). Read scope ek olarak view'da `where username = $session.user` (kişisel veri ise).
3. **SRVD** `ZSD0NN_UI_<X>`: `expose` wrapper + ortak `ZSD000_I_*VH` (value-help'ler). 4. **SRVB** `_O2` (OData V2) → activate → **publish** (Eclipse'siz, `create_rap_service.py --step srvb/srvbactivate/publish`).

**TUZAKLAR:**
- **EXCRT / kur conversion-exit alanı** (kursk/kurrf vb.) → OData publish **ERROR** "Do not use conversion exit EXCRT for property ...". Çözüm: wrapper'da `cast( <field> as abap.dec(9,5) )`. ("CAST DEC to identical type" uyarısı gelse bile exit düşer.)
- **@EndUserText.label ≤ 40 karakter** (uzun = aktivasyon uyarısı + kesilir).
- **Brand-new DDLS** = `populate_cds_views.py --force-recreate`; **mevcut güncelleme** = lock + `set_object_source` helper (force-recreate "already exists" verir). DCL şell create + ayrı `set_object_source`+activate (create_access_control source-upload'u try/except'te yutuyor).
- Frontend grid: [`ui-freestyle-odata-v2.md` §E](ui-freestyle-odata-v2.md).

## İlgili

- **Kanonik detay (tek doğru kaynak):** [`adt-rap.md`](adt-rap.md) §32
  (§32.6h det/val handler, §32.6i izolasyon+e2e, §32.6j early numbering +
  MCP lock-cache + projeksiyon ifade kısıtı)
- Frontend eşi (aynı mantık): [`ui-freestyle-odata-v2.md`](ui-freestyle-odata-v2.md)
- Checklist (yeni backend öncesi): [`checklists/ui-backend-rap-creation.md`](checklists/ui-backend-rap-creation.md)
- Standart (L2): [`../standards/05-coding-rap.md`](../standards/05-coding-rap.md)
- Governance: ADR 0005 (yasaklar) · ADR 0006 (reviewer) · ADR 0007 (MCP)
