---
applies_to: [s4_private]
---
# Reviewer Checklist — Table ALTER / Update (Z Table Field Ekleme/Değiştirme)

> Reviewer agent için mekanik checklist. Mevcut Z tabloya yeni field eklemek, field tipini değiştirmek, vb. işlemlerde `run_review.py --task table_update` çağrılır.

**Hedef obje tipi:** `TABL` (Transparent Table)
**İlgili playbook:** [`../adt-tables-structures.md`](../adt-tables-structures.md) §15 + §28

---

## Checklist

| ID | Kontrol | Validator | Severity | Kural Referansı |
|---|---|---|---|---|
| **C-TBL-NAME-01** | Tablo adı `ZSD<NNN>_T_*` pattern'inde mi? | `check_package_naming.py --type table` | BLOCKER | `.rules.md` |
| **C-TBL-SOURCE-01** | Mevcut SAP source'u GET ile alındı mı (yeni alanlar arası referans için)? | manual:source-fetched-check | BLOCKER | Update pattern |
| **C-TBL-DTEL-01** | Yeni alanların DTEL'leri SAP'de aktif mi? | `check_struct_field_dtel_active.py` ✅ `table_update` zincirinde WIRED (2026-06-10) | BLOCKER | DDIC dependency |
| **C-TBL-CUR-01** | Yeni eklenen field CURR/QUAN tipinde mi? | regex:curr-quan-detect | INFO | Tetikleyici |
| **C-TBL-CUR-02** | CURR field için reference field (CUKY) aynı tabloda var mı VEYA yeni ekleniyor mu? | `check_cds_currency_reference.py --type table` | BLOCKER | SAP DDIC kuralı |
| **C-TBL-CUR-03** | CURR field'ın hemen üstünde `@Semantics.amount.currencyCode : 'TABLE.FIELD'` qualified annotation var mı? | `check_cds_currency_reference.py` | BLOCKER | Playbook §15.3 — Vaka 2026-05-14 (T_BOOKHD) |
| **C-TBL-CUR-04** | CUKY field üzerinde `@Semantics.currencyCode : true` marker var mı? | `check_cds_currency_reference.py` | BLOCKER | Playbook §15.3 |
| **C-TBL-QUAN-01** | QUAN field için reference unit (MEINS/VRKME tarz) tabloda var mı? | `check_cds_currency_reference.py --type unit` | BLOCKER | SAP DDIC kuralı |
| **C-TBL-QUAN-02** | QUAN annotation `@Semantics.quantity.unitOfMeasure : 'TABLE.FIELD'` qualified mi? | `check_cds_currency_reference.py --type unit` | BLOCKER | Playbook §15.3 |
| **C-TBL-LOCK-01** | LOCK için doğru Accept header kullanılıyor mu? `application/*,application/vnd.sap.as+xml;dataname=com.sap.adt.lock.result` | manual:lock-header-check | BLOCKER | Playbook §14 (DTEL) / §15 |
| **C-TBL-PUT-01** | PUT source/main isteğinde If-Match HEADER YOK mu? (MSAG pattern, DTEL pattern ile aynı) | manual:if-match-check | BLOCKER | LESSONS_LEARNED — If-Match GÖNDERME |
| **C-TBL-DROP-01** | Mevcut alan SİLİNİYOR mu? (TEHLİKE — DROP risk) | `check_table_field_drop.py` ✅ WIRED (2026-06-10) — canlı SAP source diff | BLOCKER | DDIC stability — kullanıcı onayı zorunlu |
| **C-TBL-DROP-02** | DROP öncesi **WRITE-PATH kullanım analizi** yapıldı mı? "Kullanılıyor" = alana **YAZAN kod var** (ekran binding / EML MODIFY / manager set / determination / MODIFY-UPDATE). **Salt-okuma CDS exposure ≠ kullanılıyor** (ölü alan olabilir). Analiz = where-used + grep (.abap/.js/behavior/manager/UI'da SET/MODIFY). **Sorumluluk zinciri (kullanıcı araştırmaz, ONAYLAR):** (1) silmeyi öneren ajan **analizi yapar + "silinebilir" HÜKMÜNE varır + cascade'i (etkilenen CDS/SRVD/UI) çıkarır**; (2) **LİDER bitmiş hükmü+kapsamı KULLANICIYA sunar** → kullanıcı iş-kararı verir (kullanım tespitini kullanıcı YAPMAZ); (3) **yalnız gateway** uygular (feature/research tool-düzeyinde silemez). Kullanıcıya her zaman **lider** sorar (hub). Sessiz/tek-ajan veya analizsiz DROP YASAK. | manual:write-path-analysis | BLOCKER | Convention 2026-06-14 (kullanıcı) |
| **C-TBL-RENAME-01** | Mevcut alan RENAME ediliyor mu? (DROP+CREATE riski) | `check_table_field_drop.py` (rename = DROP+yeni alan olarak yakalanır) | BLOCKER | DDIC stability |
| **C-TBL-TYPE-01** | Mevcut alan TİPİ değiştiriliyor mu? (data loss riski) | `check_table_field_drop.py` (DTEL değişikliği = TYPE) | BLOCKER | DDIC stability |
| **C-TBL-STD-01** | Standart SAP DTEL referansları (NETWR, WAERK, MENGE, vb.) doğru yazıldı mı? | `check_standard_table_fields.py --type dtel` (⚠️ ORPHAN — run_review zincirinde DEĞİL; T11 wire adayı) | BLOCKER | Standart obje teyidi |
| **C-TBL-TD-01** | TD spec'teki alan listesi ile yeni source uyumlu mu (alan sayısı, sıralama)? | `manual:td-field-list-check` (oto-gate YOK; silinen-alan için `check_td_cancelled_fields` WARNING) | BLOCKER | Sprint 2A T_BOOKHD vakası |
| **C-TBL-APPEND-01** | Standart SAP tablosuna append eklenmiyor mu? (⛔ KATEGORİ A — YASAK) | regex:standard-table-append | BLOCKER | ADR 0005 |
| **C-TBL-DLI-01** | DeliveryClass değişiyor mu? | regex:delivery-class | WARNING | Genelde stabil olmalı |
| **C-TBL-MAINT-01** | DataMaintenance değişiyor mu? | regex:data-maintenance | INFO | Tercih |
| **C-TBL-ORDER-01** | Yeni iş alanı **audit bloğunun ÜSTÜNE** mi eklendi? Audit bloğu (`created_by`/`create_date`/`create_time`/`updated_by`/`update_date`/`update_time`/`last_changed_at`) **EN SONDA** kalmalı — audit'in altına alan EKLEME (append-at-end yapma). | manual:audit-last-check | WARNING | Convention 2026-06-14 (kullanıcı) |

---

## Önemli Vakalar (Bu Checklist'in Önleyeceği Patinajlar)

1. **T_BOOKHD currency annotation qualified format eksik** (Sprint 5) → **C-TBL-CUR-03** yakalar
2. **CUKY üzerinde marker eksik** → **C-TBL-CUR-04** yakalar
3. **Eski <LEGACY_SOURCE> source kopyala-yapıştır → standart alan yok** → **C-TBL-STD-01** yakalar
4. **Standart tabloya append (⛔ A)** → **C-TBL-APPEND-01** yakalar
5. **Yanlış LOCK Accept header → 406** → **C-TBL-LOCK-01** yakalar
6. **PUT'ta If-Match gönderme → 423 / 412** → **C-TBL-PUT-01** yakalar
7. **Reviewer-kör vakası (2026-06-10):** `run_review.py['table_update']` sadece CURR/QUAN + deprecated çalıştırıyordu → ~15 alan DROP eden + var olmayan DTEL'li ALTER'a **PASS** verdi (kullanıcı yakaladı). Checklist BLOCKER yazıyordu ama arkasında script YOKTU. **Fix:** `check_struct_field_dtel_active` + yeni `check_table_field_drop` zincire WIRED. Ders: **checklist satırı ≠ çalıştırılan validator** — zinciri bozuk-girdiyle adversarial test et.

---

## Update Pattern (Mevcut Tabloda Field Ekleme)

```python
# 1. GET source
r = c.session.get(url + '/source/main', ...)
src = r.text

# 2. Modify (yeni alanları ekle, annotation'ları ekle)
new_src = ...

# 3. LOCK
lock_r = c.session.post(url, params={'_action':'LOCK',...},
    headers={'Accept':'application/*,application/vnd.sap.as+xml;dataname=com.sap.adt.lock.result',
             'X-sap-adt-sessiontype':'stateful', ...})

# 4. PUT (If-Match YOK!)
put_r = c.session.put(url + '/source/main',
    params={'lockHandle': handle, 'corrNr': TR},
    headers={'Content-Type':'text/plain; charset=utf-8', ...},
    data=new_src.encode('utf-8'))

# 5. UNLOCK + ACTIVATE
```

---

## Reviewer Çıktı Formatı

(struct-creation.md ile aynı yapı)

---

## Bilinen Blind Spot'lar

- Foreign key change impact analizi
- Index/buffering değişikliği
- Append struct dahil edilen tablo değişikliği

---

## İlgili

- [`struct-creation.md`](struct-creation.md)
- [`cds-creation.md`](cds-creation.md)
- [`../adt-tables-structures.md`](../adt-tables-structures.md) §15.3 — CURR/UNIT reference
- [`../adt-domain-dtel.md`](../adt-domain-dtel.md) §26.2 — Update pattern (LOCK + PUT no If-Match)
