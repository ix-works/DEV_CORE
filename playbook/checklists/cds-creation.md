# Reviewer Checklist — CDS Creation/Update (DDLS)

> Reviewer agent için mekanik checklist. CDS view yaratma/güncelleme öncesi `run_review.py --task cds_creation` çağrılır.

**Hedef obje tipi:** `DDLS` (Data Definition Language Source)
**İlgili playbook:** [`../adt-cds.md`](../adt-cds.md)

---

## Checklist

| ID | Kontrol | Validator | Severity | Kural Referansı |
|---|---|---|---|---|
| **C-CDS-NAME-01** | View adı `ZSD<NNN>_DDL_*` pattern'inde mi? | `check_package_naming.py --type cds` | BLOCKER | `ERP/SD/<PKG>/.rules.md` |
| **C-CDS-SQLV-01** | `@AbapCatalog.sqlViewName` annotation var mı? | regex:has-sql-view-name | BLOCKER | Zorunlu DDIC field |
| **C-CDS-SQLV-02** | sqlViewName whitelist regex'ine uyuyor mu? `^ZSD001_V_[A-Z0-9]{1,5}$` | `populate_cds_views.py::validate_sql_view_names` (populate-time, reviewer-DIŞI) | BLOCKER | Playbook §17.9 — Namespace Dönüşümü |
| **C-CDS-SQLV-03** | sqlViewName toplam ≤14 char mı? | regex:sql-view-name-length | BLOCKER | SAP DDIC limiti |
| **C-CDS-LABEL-01** | `@EndUserText.label` annotation var mı ve TR dolu mu? | manual:tr-label-check | BLOCKER | ⛔ KATEGORİ D |
| **C-CDS-AUTH-01** | `@AccessControl.authorizationCheck` annotation var mı? | regex:has-auth-check | BLOCKER | ABAP CDS zorunlu |
| **C-CDS-AUTH-02** | Değeri `#NOT_REQUIRED` veya `#CHECK` mi? | regex:auth-check-value | INFO | Tercih |
| **C-CDS-DEPR-01** | `@AbapCatalog.preserveKey` kullanılmış mı? | `check_deprecated_annotations.py` | WARNING | Deprecated S/4HANA 2026+ |
| **C-CDS-WIN-01** | `OVER PARTITION BY` (window function) kullanılmış mı? | `check_window_function_compatibility.py` | BLOCKER | Bu sistem desteklemiyor (Sprint 3 vakası) |
| **C-CDS-FROM-01** | Kaynak tablolar/CDS'ler SAP'de mevcut mu? | `manual:source-exists-check` (oto-gate YOK; aktivasyon dependency'de patlar) | BLOCKER | Aktivasyon dependency |
| **C-CDS-FROM-02** | Z* kaynak CDS'leri aktif mi? | `manual:source-active-check` (oto-gate YOK) | BLOCKER | Dependency cascade |
| **C-CDS-FROM-03** | Standart tablo alanları (KNA1.name1 gibi) yeni sistemde var mı? | `check_standard_table_fields.py` (⚠️ ORPHAN — run_review zincirinde DEĞİL; T11 wire adayı) | BLOCKER | <LEGACY_SOURCE>/yeni sistem field farkı (vsartkat vakası) |
| **C-CDS-FROM-04** | ⭐ **Clean Core: std tablo (MARA/VBAP/LIPS) yerine released CDS?** `from mara` değil `from I_Product`. **KOD YAZMADAN ÖNCE** `governance/reference/released_successors.json`'a bak. Bilinçli tablo kullanıyorsan **gerekçe not et** (WARNING'i sessiz geçme). | `check_released_objects.py` | WARNING | `standards/05` §9X · `feedback_clean-core-released-cds-proaktif` |
| **C-CDS-CUR-01** | Select listesinde CURR/QUAN field var mı? | regex:curr-quan-detect | INFO | Tetikleyici |
| **C-CDS-CUR-02** | CURR field'ın annotation'ı `@Semantics.amount.currencyCode` qualified mi? | `check_cds_currency_reference.py` | BLOCKER | Playbook §15.3 |
| **C-CDS-CUR-03** | QUAN field'ın annotation'ı `@Semantics.quantity.unitOfMeasure` qualified mi? | `check_cds_currency_reference.py` | BLOCKER | Playbook §15.3 |
| **C-CDS-NS-01** | Eski <LEGACY_SOURCE> source'tan kopyalanmışsa `zsd_007_` → `zsd001_` namespace dönüştürüldü mü? | `manual:namespace-conversion-check` (oto-gate YOK) | BLOCKER | TD spec kuralı |
| **C-CDS-NS-02** | Eski sistem field rename'leri uygulandı mı (örn. `teklif` → `order_amount`)? | `manual:<legacy_source>-field-rename-check` (oto-gate YOK; silinen-alan için `check_td_cancelled_fields` WARNING var, rename için YOK) | BLOCKER | LESSONS_LEARNED #2 |
| **C-CDS-KEY-01** | En az 1 `key` field var mı? | regex:has-key-field | WARNING | Tüm view'lar key gerektirir |
| **C-CDS-AGG-01** | `sum()` / `count()` kullanılmış ise `group by` var mı? | regex:group-by-check | BLOCKER | SQL kural |
| **C-CDS-TD-01** | TD spec dosyası `.md` var mı? (`td_spec_check.py` zaten pre-flight'ta çalışır) | `td_spec_check.py` | BLOCKER | LESSONS_LEARNED #2 |
| **C-CDS-TD-02** | TD spec'teki silinen alanlar source'tan kaldırıldı mı? | `td_spec_check.py` | BLOCKER | LESSONS_LEARNED #2 |
| **C-CDS-LANG-01** | Aktivasyon öncesi TR text doğrulama (description, label hep TR olacak) | manual:tr-text-final-check | WARNING | ⛔ KATEGORİ D |
| **C-CDS-UNION-01** | **MUST** — `union all` içeren view-entity'de 3 kural peşinen uygulandı mı: (a) WHERE'de `NOT EXISTS`/`EXISTS` subquery YOK → LEFT JOIN+`IS NULL` anti-join; (b) element `@Semantics.*` YALNIZ 1.(ilk) dalda; (c) quantity/amount @Semantics varsa header `@Metadata.ignorePropagatedAnnotations:true`. Aksi her biri AYRI aktivasyon-fail turu (bug-gate yakalayamaz, yalnız aktivasyonda çıkar). | `manual:union-rules` (⚠️ validator-aday — 3'ü de statik regex tespit edilebilir; T11 wire) | BLOCKER | `playbook/adt-cds.md` T4 · ZSD001_I_BATCH_STOCK 2026-06-19 |
| **C-CDS-CONVEXIT-01** | **MUST** — conversion-exit'li DTEL alanı (`/scwm/de_huident`=HUID, kur/EXCRT) OData/SADL'a expose ediliyorsa exit publish'i kırar ("Do not use conversion exit X for property Y" → `$metadata` 500). İKİ DURUM AYRI: **(a) READ-ONLY/display** → `cast( <field> as abap.char(<len>) )` ile exit DÜŞ (cast'lı element computed/read-only olur, sorun değil). **(b) YAZILABİLİR/persist (RAP managed mapping)** → cast YASAK: cast'lı element computed olur → BDEF map edemez + FE yazamaz → **cast writability'i öldürür**. Yazılabilir conv-exit alanı için TEK temiz yol = alanın **exit-siz Z-DTEL'e** çevrilmesi (tablo ALTER + Z-DTEL, ADR 0005-A/D **kullanıcı onayı + ad** gerektirir). "Yazılabilir + conv-exit" aynı anda OData V2'de İMKÂNSIZ. | `manual:convexit-odata` (⚠️ validator-aday; T11 wire) | BLOCKER | `playbook/adt-cds.md` T5 · `ui-backend-rap.md` §150 · ZSD001 HuIdent 2026-06-19 |
| **C-CDS-FIELDRM-01** | **MUST** — Aktif bir CDS interface'ten alan KALDIRIRKEN sıra TERS: ÖNCE tüketici (projeksiyon/consumption + onu expose eden SRVB) re-activate, SONRA interface. Interface'i önce activate edersen `Field X is still used in projection list in entity Y` hatası. (Eklemede sıra normal: interface→projeksiyon.) | `manual:field-removal-order` | BLOCKER | RAP bağımlılık · ZSD001_C_SIPSE_ITEM 2026-06-19 |
| **C-CDS-2PHASE-01** | **MUST** — Bir helper/alt-view'ın KEY/expose alanını değiştirip (ör. `Material`→`ProductUUID`) AYNI ANDA tek tüketicinin JOIN'ini o yeni alana çevirmek = **atomik-aktive-edilemez DEADLOCK** (her obje karşı-tarafın ESKİ-aktif sürümüne doğrulanır → iki yön de kırılır; sıralama VE circular `/activation` POST çözmez). Çözüm = **İKİ-FAZ:** (1) helper'a yeni alanı EKLE eski alanı KORU → aktive (eski tüketiciye karşı geçer) → (2) tüketici join'ini yeni alana çevir → aktive (yeni helper'a karşı geçer) → (3) ayrı tur helper'dan eski alanı kaldır. Tek-turda key-change+join-change YAPMA. | `manual:cds-key-join-2phase` (⚠️ validator-aday: aynı changeset'te helper key-değişimi + consumer join-değişimi statik tespit; T11) | BLOCKER | `adt-rap.md` §C3 varyantı · ZSD001_I_BATCH_STOCK 2026-06-19 |
| **C-CDS-QTYEXPR-01** | **MUST** — quantity/amount-semantic taşıyan alan (CURR/QUAN; `@Semantics.quantity.*`/`amount.*` ile expose edilen kaynak DB alanı, örn. `quantity`) aritmetik ifadede (`a - b`, `a + b`, `a * b`) KULLANILAMAZ → aktivasyon FAIL ("Amounts and quantities are not allowed in expression"). İfadeye girmeden ÖNCE `cast( <field> as abap.dec(<len>,<dec>) )` ile semantik SIYIR, sonra hesapla, dışta tip-sabitle. (Bakiye = Quantity − DeliveredQty vakası 2026-06-19.) | `manual:qty-in-expr` (⚠️ validator-aday — `@Semantics.quantity/amount` alanının `+-*/` ifadesinde cast'sız kullanımı statik regex; T11 wire) | BLOCKER | `playbook/adt-cds.md` · ZSD001_I_SIPSE_ITEM 2026-06-19 |
| **C-CDS-AGGUNIT-01** | **MUST** — Aggregation (`max`/`min`/`sum`) bir **UNIT (MEINS/`gewei`/`vrkme`) veya CUKY (para birimi) tipli alana** UYGULANAMAZ → aktivasyon FAIL ("Function MAX: Type UNIT of Parameter 1 not supported (...QUAN CHAR D)"). Bu alanlar quantity/amount'un **birim referansıdır** → aggregate ETME, **`group by`'a koy** (`Item.gewei as WeightUnit` + group-by'a `Item.gewei`). Malzeme/birim başına tekil olduğundan granülerlik değişmez; `@Semantics.quantity.unitOfMeasure` için zaten grouped kolon gerekir. (Static review/bug-gate YAKALAYAMADI — yalnız aktivasyonda çıktı.) | `manual:agg-unit-cuky` (⚠️ validator-aday — `max/min/sum(<UNIT\|CUKY-tipli-alan>)` statik tespit; T11 wire) | BLOCKER | ZSD001_I_TRDOC_PRINT_ITEM 2026-06-30 |
| **C-CDS-CONSUME-01** | **MUST** — BO'suz salt-okunur tüketim/OData-lookup view'ı **`as select from <I_view>`** olmalı; **`as projection on` YASAK** (+ `root` YASAK, `redirected to` YASAK). `as projection on` → aktivasyon FAIL "Transactional Projection View must be part of a business object" (projection=RAP transactional→BDEF/BO ister); `root ... as projection on <non-root>` → "ROOT keyword not valid". Child `$expand` = **yeniden-bildirilen association** (`association [1..*] to <C_child> as _X on $projection... `), `redirected to` DEĞİL. `@Semantics`/`@Metadata.allowExtensions` consumption'da bildir. (Playbook §T3'te VARDI — backend uygulamadı, bug-gate yakalayamadı: checklist eksiğiydi.) | `manual:consume-select-not-projection` (⚠️ validator-aday — `as projection on <I_*>` + BDEF-yok statik tespit; T11 wire) | BLOCKER | `playbook/adt-cds.md` §T3 · ZSD001_C_TRDOC_PRINT 2026-06-30 |

---

## Önemli Vakalar (Bu Checklist'in Önleyeceği Patinajlar)

1. **`OVER PARTITION BY` aktivasyon fail** (Sprint 3, ORDER_SCHED_LINES) → **C-CDS-WIN-01** yakalar
2. **sqlViewName whitelist ihlali** (`ZSD001_V_BOOKDC` 6 char) → **C-CDS-SQLV-02** yakalar
3. **vsartkat field yok** (T173) → **C-CDS-FROM-03** yakalar
4. **deprecated preserveKey** → **C-CDS-DEPR-01** yakalar
5. **`teklif as teklif`** (rename atlanmış) → **C-CDS-NS-02** yakalar
6. **Window function alternatifi (ABAP class) sorulmadan CDS'te denenmiş** → **C-CDS-WIN-01** ABAP'a yönlendir

---

## Reviewer Çıktı Formatı

(struct-creation.md ile aynı yapı — verdict + checklist_results + known_blind_spots + net_decision)

---

## Bilinen Blind Spot'lar

- Recursive CDS bağımlılığı (A → B → C → A) check yok
- Multi-language label tutarsızlığı (sadece TR var, EN check yok)
- @VDM annotation eksiklikleri (analytical CDS için)
- Composition vs Association kullanımı (RAP CDS için — bu projede yok)

---

## İlgili

- [`struct-creation.md`](struct-creation.md)
- [`table-update.md`](table-update.md)
- [`../adt-cds.md`](../adt-cds.md) §17 — CDS playbook
