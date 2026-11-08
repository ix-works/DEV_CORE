---
applies_to: [s4_private]
---
# Reviewer Checklist — Struct Creation (DDIC Structure)

> Bu dosya **reviewer agent** için mekanik checklist. Coordinator yeni Z struct (DDIC structure) yaratırken/güncellerken `run_review.py --task struct_creation` çağrılır → reviewer bu listeyi tarar.

**Hedef obje tipi:** `STRU` / DDIC structure (ZSD001_S_*)
**İlgili playbook:** [`../adt-tables-structures.md`](../adt-tables-structures.md) §15 + §28

---

## Checklist

| ID | Kontrol | Validator | Severity | Kural Referansı |
|---|---|---|---|---|
| **C-STR-NAME-01** | Obje adı `ZSD<NNN>_S_<NAME>` regex'ine uyuyor mu? | `check_package_naming.py --type struct` | BLOCKER | `ERP/SD/ZSD001_CLC/.rules.md` "Structure" satırı |
| **C-STR-NAME-02** | Adın uzunluğu ≤30 char mı? | manual:string-length-check | BLOCKER | SAP DDIC name limit |
| **C-STR-LABEL-01** | `@EndUserText.label` annotation var mı? | regex:has-label | BLOCKER | Playbook §15.2 |
| **C-STR-LABEL-02** | Label TR ve dolu mu (boş değil, İngilizce değil)? | manual:tr-text-check | BLOCKER | ⛔ KATEGORİ D — Z'li obje TR text zorunluluğu |
| **C-STR-LABEL-03** | Label master language `TR` ile uyumlu mu? | regex:master-language | WARNING | Playbook §15.2 |
| **C-STR-FIELD-01** | Her field için DTEL referansı var mı (built-in tip değil, custom DTEL)? DTEL'siz (yerleşik `abap.*` tipli) her alan **listelenir** (`alan · tip · obje`); listelenen her alan kullanıcının tasarım onay kaydında adıyla geçmeli (BE-13). Bilinçli karar: alan satırında ya da hemen üstünde `// dtel-istisna: <gerekçe>` → "istisna (gerekçeli)" sayılır, uyarı vermez; gerekçesiz işaret uyarı kalır | `check_ddic_builtin_fields.py` (`run_review` struct_creation zincirinde WARNING; listeler, engellemez) | WARNING | Mimari tercih + `claude/rules/sap-source-protokolu.md` "Yeni DDIC tablo" (mevcut DTEL kullan) — şiddet zincirdeki WARNING ile aynı yazıldı (eski INFO'nun arkasında çalışan kontrol yoktu; DEV_CORE #406) |
| **C-STR-FIELD-02** | Kullanılan tüm `ZSD<NNN>_E_*` DTEL'ler SAP'de aktif mi? | `check_struct_field_dtel_active.py` | BLOCKER | DDIC dependency zinciri |
| **C-STR-FIELD-03** | Standart SAP DTEL referansları (MANDT, ERNAM, ERDAT, vb.) doğru ad kullanıyor mu? | `check_standard_table_fields.py` (⚠️ ORPHAN — run_review zincirinde DEĞİL; T11 wire adayı) | BLOCKER | Standart obje varlık teyidi |
| **C-STR-FIELD-04** | İki field aynı isimde mi (case-insensitive duplicate)? | regex:duplicate-field-name | BLOCKER | DDIC kural |
| **C-STR-CUR-01** | CURR/QUAN field var mı? | regex:curr-quan-detect | INFO | Tetikleyici |
| **C-STR-CUR-02** | CURR field var ise, hemen üstünde `@Semantics.amount.currencyCode` annotation var mı? | `check_cds_currency_reference.py` | BLOCKER | Playbook §15.3 |
| **C-STR-CUR-03** | Annotation değeri qualified format `'TABLE.FIELD'` mi? | `check_cds_currency_reference.py` | BLOCKER | Playbook §15.3 — "Sadece field adı yazılırsa 'annotation uncomplete' hatası" |
| **C-STR-CUR-04** | CURR field'ın başvurduğu para birimi (CUKY) alanı mevcut mu? Başvuru **aynı yapıya** ise alan yapıda var mı (yoksa BLOCKER) — alan var ama DTEL'i ortak sözlükte (`scripts/utils/ddic_semantics.py`) değilse WARNING ("tip sözlükten doğrulanamadı"). Başvuru **başka tabloya/yapıya** ise kapı onu okumaz, yalnız INFO notu basar. Ad büyük/küçük harf duyarsız karşılaştırılır (tablo karşılığı: `table-update.md` C-TBL-CUR-02) | `check_cds_currency_reference.py` | BLOCKER (alan yok) · WARNING (tip doğrulanamadı) | SAP DDIC: CURR alanı bir CUKY alanına başvurur; başvuru başka tabloda olabilir (DEV_CORE Issue #399) |
| **C-STR-CUR-05** | Referans edilen YEREL field üzerinde `@Semantics.currencyCode : true` marker var mı? Sözlükteki CUKY alanlarına ek olarak, CURR'un başvurduğu her yerel alana uygulanır (Z'li DTEL'li ya da yerleşik `abap.cuky`) | `check_cds_currency_reference.py` | BLOCKER | Playbook §15.3 |
| **C-STR-UNIT-01** | QUAN field var ise, `@Semantics.quantity.unitOfMeasure` annotation qualified mi? | `check_cds_currency_reference.py --type unit` | BLOCKER | Playbook §15.3 (CURR ile aynı pattern) |
| **C-STR-UNIT-02** | Referans edilen unit field üzerinde `@Semantics.unitOfMeasure : true` marker var mı? | `check_cds_currency_reference.py --type unit` | BLOCKER | Playbook §15.3 |
| **C-STR-DEPR-01** | `@AbapCatalog.preserveKey` annotation kullanılmış mı? | `check_deprecated_annotations.py` | WARNING | Deprecated (Sprint 5'te keşfedildi) |
| **C-STR-KAP-01** | <LEGACY_SOURCE> md'sinde "silinen alan" var ise yeni source'tan kaldırıldı mı? | `manual:legacy-deleted-field-check` (silinen-alan denetimi PROJE-katmanıdır: varsa `scripts/validators-local/` proje-validator'ı WARNING verir; core oto-gate YOK) | BLOCKER | LESSONS_LEARNED #2 — Spec Disiplini |
| **C-STR-KAP-02** | Field rename'ler (eski → yeni) doğru uygulanmış mı? | `manual:field-rename-check` (oto-gate YOK) | BLOCKER | TD spec |
| **C-STR-LANG-01** | Mevcut sistemdeki obje (varsa) ile aynı `masterLanguage="TR"` mi? | regex:master-language | WARNING | ⛔ KATEGORİ D |

---

## Reviewer Çıktı Formatı

```yaml
review_result:
  verdict: PASS | WARNING | BLOCKER
  task_type: struct_creation
  artifact: ERP/SD/ZSD001_CLC/structures/ZSD001_S_X.ddls.asddls

  checklist_results:
    - id: C-STR-NAME-01
      status: PASS
      validator_output: "check_package_naming.py: OK"
    - id: C-STR-CUR-03
      status: FAIL
      rule_reference: "playbook/adt-tables-structures.md §15.3"
      quote_from_rule: "Annotation isimleri (case-sensitive): @Semantics.amount.currencyCode ... Her ikisinde de referans formatı 'TABLE_NAME.FIELD_NAME' (qualified)"
      violation_in_artifact: "ZSD001_S_X.ddls.asddls:14 — annotation 'order_currency' (qualified eksik)"
      suggested_fix: "'order_currency' → 'zsd001_s_x.order_currency'"
      validator_output: "check_cds_currency_reference.py: FAIL line 14"
    # ... her madde için

  known_blind_spots:
    - "Field-level enhancement (append struct) checki yok"
    - "Pool/cluster tablo struct'ları için özel kural test edilmedi"

  net_decision_for_coordinator: |
    1 BLOCKER bulundu (C-STR-CUR-03). Şu satırı düzelt:
      Line 14: '...'order_currency' → 'zsd001_s_x.order_currency'
    Düzelttikten sonra tekrar review iste.
```

---

## Reviewer'ın Atlamaması Gereken Kontroller (Fail-Fast)

Her checklist maddesi için kesin status. Atlamak/genel cevap vermek yasak.

**"Sanırım OK"** veya **"genelde böyle yapılır"** **YASAK** — kanıt yoksa FAIL işaretle.

---

## Bilinen Blind Spot'lar (Henüz Otomatize Edilmemiş)

Aşağıdaki konular henüz validator'la kapsanmadı; reviewer manuel değerlendirir:

- Field-level enhancement (append struct varlığı)
- Custom field type definitions
- Pool/cluster/IntTab struct ayrımı
- Multi-language label tutarlılığı (sadece TR check var)

Bu blind spot'lar **T10 trigger** ile zamanla otomatize edilir.

---

## İlgili

- [`cds-creation.md`](cds-creation.md) — CDS yaratma checklist'i (benzer pattern, ek CDS-spesifik check'ler)
- [`table-update.md`](table-update.md) — Tablo ALTER (CURR field ekleme vakası)
- [`../adt-tables-structures.md`](../adt-tables-structures.md) §15 — Z tablo/struct playbook
