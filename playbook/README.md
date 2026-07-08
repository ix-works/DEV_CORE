---
layer: L3
scope: project-wide
type: index
last-updated: 2026-05-14
---

# Playbook — SAP ADT Operasyonel Pattern Bankası

Bu klasör **L3 katman** dosyaları içerir: SAP ADT REST işlemleri için **deneme-yanılma ile bulunmuş çalışan pattern'ler**, denenmiş başarısız yollar ve gotcha'lar.

> **Kaynak Disiplini:** Bu dosyalar `SAP_ADT_PLAYBOOK.md` (eski 143 KB tek dosya) bölünerek oluşturuldu (2026-05-14, Adım 3). Section'lar obje tipine göre dağıtıldı.

---

## Dosya İndeksi — Obje Tipi → Hangi Dosya?

| Obje Tipi / İşlem | Dosya | Kapsam |
|---|---|---|
| Disiplin, hızlı erişim, genel prensipler, bağlantı | [`00-discipline-and-principles.md`](00-discipline-and-principles.md) | Her ADT işine başlamadan önce |
| Logon, Download, Push/Activate, Lock, SQL, Package, Transport, Search, Where-used, ATC, OData Metadata | [`adt-foundation.md`](adt-foundation.md) | §1-§11 — temel ADT işlemleri |
| **DDIC Structure**, **Table Type**, **Z Tablo (TABL/DT)** | [`adt-tables-structures.md`](adt-tables-structures.md) | §12, §13, §15 |
| **Domain + Data Element (DTEL)** | [`adt-domain-dtel.md`](adt-domain-dtel.md) | §14 |
| **Lock Object (ENQU/DL)** | [`adt-lock-objects.md`](adt-lock-objects.md) | §16 |
| **CDS View (DDLS/DF)** | [`adt-cds.md`](adt-cds.md) | §17 |
| **Mesaj Sınıfı (MSAG)** | [`adt-message-class.md`](adt-message-class.md) | §18 |
| **ABAP Class** (create, OSQLC, push+activate flow) | [`adt-classes.md`](adt-classes.md) | §19, §20, §26 |
| **ABAP Report (PROG/P)** | [`adt-programs.md`](adt-programs.md) | §21 |
| **Function Group + Function Module** (create/imza/RFC) + **Klasik Dynpro ekranı & GUI status ÜRETİMİ** | [`adt-fugr-functions.md`](adt-fugr-functions.md) | FG/FM tam pattern + §6 `ZSD000_FM_SCREEN_GEN` (RPY_DYNPRO_INSERT + RS_CUA, SOAP-RFC) — **yeni klasik ALV/Dynpro programında ÖNER** |
| ABAP coding patterns (Range, FAE, İç tablo, Kur dönüşümü) | [`coding-patterns.md`](coding-patterns.md) | §22-§25 |
| OData services (Pricing simulation, Function Import, UpdateSO, BAPIRET2) | [`odata-services.md`](odata-services.md) | §27-§30 |
| Bilinen hatalar ve çözümlü durumlar | [`known-errors.md`](known-errors.md) | §31 |
| Hata pattern kataloğu + trigger phrases | [`lessons-learned.md`](lessons-learned.md) | Cross-cutting |
| **RAP** (view entity, BDEF, behavior, service def/binding, publish) | [`adt-rap.md`](adt-rap.md) | §32 — ⚠️ ilk kez (ORDER pilotu); kanıtlanmış/kanıtlanmamış ayrımlı |
| **MCP tool kullanımı** (ADR 0007) | [`adt-mcp.md`](adt-mcp.md) | 11 typed tool — coordinator için |
| **Freestyle UI5 + OData V2** (tarayıcı tarafı) | [`ui-freestyle-odata-v2.md`](ui-freestyle-odata-v2.md) | ORDER UI patinaj tecrübesi + §0 PRE-FLIGHT + [checklist](checklists/ui-freestyle-creation.md) |
| **UI uygulaması RAP backend** (CDS/BDEF/behavior/SRVD tecrübe merceği) | [`ui-backend-rap.md`](ui-backend-rap.md) | ORDER backend patinajı + §0 PRE-FLIGHT + [checklist](checklists/ui-backend-rap-creation.md); kanonik = `adt-rap.md` §32 |

---

## Playbook ↔ Script Bağlantısı

Her playbook section'ı `scripts/` altındaki **kanonik implementasyon**'a referans verir:

| Tip | Script | Playbook Bölümü |
|---|---|---|
| Domain | [`scripts/create_domain.py`](../scripts/create_domain.py) | `adt-domain-dtel.md` |
| Data Element | [`scripts/create_dataelement.py`](../scripts/create_dataelement.py) | `adt-domain-dtel.md` |
| Structure | [`scripts/create_structure.py`](../scripts/create_structure.py) | `adt-tables-structures.md` |
| Table Type | [`scripts/create_table_type.py`](../scripts/create_table_type.py) | `adt-tables-structures.md` |
| Z Table | [`scripts/create_table.py`](../scripts/create_table.py) | `adt-tables-structures.md` |
| Lock Object | [`scripts/create_lock_object.py`](../scripts/create_lock_object.py) | `adt-lock-objects.md` |
| CDS View | [`scripts/create_cds_view.py`](../scripts/create_cds_view.py) | `adt-cds.md` |
| Message Class | [`scripts/create_message_class.py`](../scripts/create_message_class.py) | `adt-message-class.md` |
| Class | [`scripts/create_object.py`](../scripts/create_object.py), [`push_object.py`](../scripts/push_object.py) | `adt-classes.md` |
| Function Group | [`scripts/create_function_group.py`](../scripts/create_function_group.py) | `adt-fugr-functions.md` (placeholder) |
| Function Module | [`scripts/create_function_module.py`](../scripts/create_function_module.py) | `adt-fugr-functions.md` (placeholder) |
| Populate batch | [`scripts/populate_*.py`](../scripts/) | İlgili obje dosyası |
| Behavior Definition | [`scripts/create_behavior_definition.py`](../scripts/create_behavior_definition.py) | `adt-rap.md` §32.2 |
| Behavior Impl. | [`scripts/create_behavior_implementation.py`](../scripts/create_behavior_implementation.py) | `adt-rap.md` §32.3 |
| Metadata Extension | [`scripts/create_metadata_extension.py`](../scripts/create_metadata_extension.py) | `adt-rap.md` §32 |
| RAP view entity batch | [`scripts/populate_cds_views.py`](../scripts/populate_cds_views.py) | `adt-rap.md` §32.1 (RAP-aware pre-flight) |

`scripts/validators/check_scripts_documented.py` her `create_*.py`, `populate_*.py`, `run_*.py` script'inin playbook'ta referans verildiğini doğrular (LESSONS_LEARNED #4 prensibi).

---

## Yeni Pattern Eklenmesi (T1-T2 Trigger)

Aşağıdakilerden biri olduğunda forward progress'ten önce ilgili playbook dosyasına ekleme yapılır:

- **T1** — Bir SAP ADT işlemi başarısız denemelerden sonra başarılı oldu
- **T2** — Daha önce playbook'ta olmayan bir obje tipi/scenario işlendi

Format: `00-discipline-and-principles.md`'deki "ÇALIŞAN YÖNTEM" + "DENENEN VE BAŞARISIZ YOLLAR" + "KRİTİK NOTLAR" şablonu.

## İlgili

- [`../standards/`](../standards/) — L2 stabil kurumsal standartlar
- [`../CLAUDE.md`](../CLAUDE.md) — Session protokolü + trigger özeti
- [`../scripts/`](../scripts/) — Kanonik implementasyon kütüphanesi
- [`lessons-learned.md`](lessons-learned.md) — Hata pattern kataloğu
