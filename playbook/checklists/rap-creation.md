---
applies_to: [s4_private]
---
# Reviewer Checklist — RAP Object Creation (view entity / BDEF / SD / SB)

> Reviewer agent için mekanik checklist. RAP SAP-yazması öncesi
> `run_review.py --task rap_cds_creation | rap_bdef_creation | rap_service_binding` çağrılır.

**Hedef obje tipleri:** `DDLS/DF` (view entity), `BDEF/BDO`, `CLAS/OC` (behavior pool), `SRVD/SRV`, `SRVB/SVB`
**İlgili playbook:** [`../adt-rap.md`](../adt-rap.md) §32 · **Standart:** [`../../standards/05-coding-rap.md`](../../standards/05-coding-rap.md)

---

## Checklist — Ortak (her RAP objesi)

| ID | Kontrol | Validator | Severity | Kural |
|---|---|---|---|---|
| **C-RAP-NAME-01** | Ad NTTDATA RAP prefix'inde mi? (I_/C_/R_/E_ view; SD `UI`/`API`; SB `_O2`/`_O4`; sınıf `ZCL_SD001_`) | `check_package_naming.py` | BLOCKER | `01-naming.md` §4.2/§4.4.1 |
| **C-RAP-NAME-02** | BDEF adı root view entity adıyla **aynı** mı? | manual | BLOCKER | SAP zorunlu |
| **C-RAP-PKG-01** | Obje ZSD001_CLC paketinde mi (cross-pkg sızıntı yok)? | `check_object_in_correct_pkg.py` | BLOCKER | ADR 0003 |
| **C-RAP-TR-01** | Transport kullanıcının verdiği aktif TR mi? Yeni TR/paket YOK? | manual | BLOCKER | ⛔ ADR 0005 C |
| **C-RAP-TXT-01** | `@EndUserText.label`/başlık TR, tam, **tahmin değil** (spec/<LEGACY_SOURCE> kaynaklı)? | manual:tr-label-check | BLOCKER | ⛔ ADR 0005 D |
| **C-RAP-STD-01** | Std obje/tablo direkt yazımı yok? (managed EML sadece Z tablo; std → released BAPI) | manual | BLOCKER | ⛔ ADR 0005 A/B |
| **C-RAP-REL-01** | ⭐ **Clean Core: interface CDS std tablo (VBAP/LIPS/MARA) yerine released CDS okuyor mu?** **KOD YAZMADAN ÖNCE** `released_successors.json` bak (MARA→I_Product). Tüm-tip released-API için native ATC "Usage of APIs". Bilinçli tablo ise gerekçe; WARNING sessiz geçilmez | `check_released_objects.py` | WARNING | `standards/05` §9X · `feedback_clean-core-released-cds-proaktif` |
| **C-RAP-ACT-01** | Aktivasyon sonrası `adtcore:version="active"` **VE aktif source dolu/valid** doğrulandı mı? (status-200/script-return YETMEZ — boş-shell de "var" döner; 2026-06-10 ITEM/DORBN boş-source vakası) | `check_sap_active_version.py` (içerik-farkındalıklı, 2026-06-10) — raw create scriptleri de `verify_active()` ile çağırır | BLOCKER | Dependency cascade + [[feedback_inline-post-empty-source-trap]] |
| **C-RAP-LANG-01** | Post-create `adt_get include_source=false` → `adtcore:masterLanguage="TR"` mı? (⚠️ MCP post_shell EN yaratır — class/BDEF/SRVD raw REST + TR shell) | `manual:tr-master-lang-check` + `check_sap_master_language.py` (⚠️ ORPHAN — script mevcut, hiçbir runner'a wire EDİLMEMİŞ; T11 wire adayı) | BLOCKER | ⛔ ADR 0005 D · `feedback_mcp-post-shell-en-master-lang` |

## Checklist — View Entity (rap_cds_creation)

| ID | Kontrol | Validator | Severity | Kural |
|---|---|---|---|---|
| **C-RAP-VE-01** | `define [root] view entity` kullanılmış mı (klasik `define view` DEĞİL)? | regex | BLOCKER | RAP zorunlu |
| **C-RAP-VE-02** | `@AbapCatalog.sqlViewName` **YOK** mu? (view entity'de varsa hata) | regex | BLOCKER | View entity sqlView taşımaz |
| **C-RAP-VE-03** | Field adları `ZSD001_T_*`'tan DDIC-doğrulanmış mı (tahmin yok)? | `check_standard_table_fields.py` (⚠️ ORPHAN — run_review zincirinde DEĞİL; T11 wire adayı) | BLOCKER | `feedback_<legacy_source>-field-adlari-...` |
| **C-RAP-VE-04** | `@AccessControl.authorizationCheck` var mı? | regex | BLOCKER | CDS zorunlu |
| **C-RAP-VE-05** | Composition/association root↔child tutarlı (key path, on-cond)? | manual | BLOCKER | RAP model bütünlüğü |
| **C-RAP-VE-06** | `OVER PARTITION BY` (window fn) yok mu? | `check_window_function_compatibility.py` | BLOCKER | Sistem desteklemiyor (Sprint 3) |
| **C-RAP-VE-07** | CURR/QUAN field annotation qualified mı? | `check_cds_currency_reference.py` | BLOCKER | Playbook §15.3 |
| **C-RAP-VE-08** | `@AbapCatalog.preserveKey` yok mu? | `check_deprecated_annotations.py` | WARNING | Deprecated |

## Checklist — Abstract Entity (action param/result — SELECT'siz)

> ⚠️ Abstract entity (`define [root] abstract entity`, action `parameter`/`result`) = **view-entity DEĞİL**. SELECT/SQL-view taşımaz → SELECT bekleyen araçlar (`create_cds_view.py` "no SELECT", `populate_cds_views.py` sprint-gate) PATLAR. Kök-sebep: nakliye param/result patinajı 2026-06-23.

| ID | Kontrol | Severity | Kural |
|---|---|---|---|
| **C-RAP-AE-01** | `as select from` YOK + `define [root] abstract entity` VAR → **abstract reçetesi** mi seçildi (view-entity araçları DEĞİL)? Inline-source POST shell → toplu activate → aktif-source'ta `abstract entity` doğrula. `create_cds_view`/`populate_cds_views` KULLANMA. | BLOCKER | `adt-cds.md` §"ABSTRACT ENTITY" + [[feedback_playbook-once-oku]] |
| **C-RAP-AE-02** | Param entity'de `@EndUserText.label` TR + alan tipleri DTEL/built-in doğrulanmış (tahmin yok)? | BLOCKER | ⛔ ADR 0005 D |

## Checklist — BDEF (rap_bdef_creation)

| ID | Kontrol | Severity | Kural |
|---|---|---|---|
| **C-RAP-BD-01** | implementation type gerekçeli (managed=Z-only; unmanaged=std→released BAPI)? | BLOCKER | 05-coding-rap §5 |
| **C-RAP-BD-02** | Draft kararı açık (varsayılan draft'sız; draft varsa `ZSDxxx_A_*_D`)? | BLOCKER | Pilot kararı |
| **C-RAP-BD-03** | Numbering NR objesi **kullanıcı kaynaklı** (AI NR yaratmıyor)? | BLOCKER | ⛔ ADR 0005 C |
| **C-RAP-BD-04** | EML std tabloya yazmıyor; tek MODIFY bloğu, %cid unique, COMMIT ENTITIES yok? | BLOCKER | Playbook §29 |
| **C-RAP-BD-05** | **MUST** — `validation`/`determination ... on save` tetikleyicisinde `update` varsa `create` de VAR mı? Tek başına `{ ... update; }` aktivasyon FAIL eder: "The trigger update is only allowed in combination with create here." Repo-geneli desen istisnasız `{ create; update; }` (ORDER/BOOKING/SEVKEMRI). `delete;` ve `create;` tek-başına serbest. (Statik regex: `on save {` bloğunda `update` var + `create` yok → BLOCKER.) | BLOCKER | RAP semantik · ZSD001_I_SE_A 2026-06-19 |

## Checklist — Service Binding + Publish (rap_service_binding)

| ID | Kontrol | Severity | Kural |
|---|---|---|---|
| **C-RAP-SB-01** | SD `expose` sadece projection/query CDS (interface view doğrudan değil)? | BLOCKER | 05-coding-rap §7 |
| **C-RAP-SB-02** | Binding tipi/suffix doğru (`_O2`=V2, `_O4`=V4 hedge)? | BLOCKER | `01-naming.md` §4.2 |
| **C-RAP-SB-03** | Publish **AI-otonom** çalıştı, operatör adımı YOK? | BLOCKER | ⛔ pilot premisi (RAP-vs-SEGW) |
| **C-RAP-SB-04** | Publish sonrası `GET .../ZSD001_UI_ORDER_O2/$metadata` = 200 doğrulandı mı? | BLOCKER | Canlı kanıt |
| **C-RAP-SB-05** | Publish başarısız → STOP + kullanıcıya rapor (pilot GATE)? | BLOCKER | ADR 0006 + PILOT §6 |

---

## Önemli Vakalar (Bu Checklist'in Önleyeceği Patinajlar)

1. View entity'ye klasik `@AbapCatalog.sqlViewName` eklenmesi → **C-RAP-VE-02**
2. BDEF adının root entity'den farklı verilip aktivasyon fail → **C-RAP-NAME-02**
3. Managed behavior EML'inin std tabloya yazması (ADR 0005 B) → **C-RAP-STD-01 / C-RAP-BD-04**
4. Publish'in sessizce operatör adımı gerektirmesi (SEGW'ye geri düşmek) → **C-RAP-SB-03/04**
5. RAP CDS text'inin tahmin edilmesi → **C-RAP-TXT-01**

## Reviewer Çıktı Formatı

(struct-creation.md / cds-creation.md ile aynı — verdict + checklist_results + known_blind_spots + net_decision)

## Bilinen Blind Spot'lar

- BDEF/SD/SB için **deterministik validator yok** (manual + bu checklist) — pilot olgunlaşınca script yazılır (T10)
- Publish endpoint pattern kanıtlanmadı → checklist davranışsal kontrol; otomasyon spike sonrası
- Composition derinliği >2 seviye check yok
- Draft UX (bilerek kapsam dışı, draft'sız pilot)

## İlgili

- [`cds-creation.md`](cds-creation.md) · [`struct-creation.md`](struct-creation.md)
- [`../adt-rap.md`](../adt-rap.md) §32 — RAP playbook
- [`../../standards/05-coding-rap.md`](../../standards/05-coding-rap.md) — L2 RAP standardı
