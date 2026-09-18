---
name: feedback_edid4-sdata-lchr-dtint2-ile-okunur
description: "IDoc segment verisi (EDID4.SDATA, LCHR) adt_sql_query ile OKUNUR — koşul: uzunluk alanı DTINT2 ile BİRLİKTE ve AÇIK alan listesiyle; SELECT * ve tek başına sdata 400 verir (Z class gerekmez)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f911c8cf-83f3-4ff2-bd38-ae5ee4790ae5
---

Canlı IDoc'un **segment içeriğini** okumak için özel bir Z sınıfına gerek YOK.
`adt_sql_query` ile doğrudan okunur — tek koşul, LCHR alanının **kendi uzunluk alanıyla
(`DTINT2`) BİRLİKTE ve AÇIK alan listesiyle** seçilmesi:

```sql
SELECT segnum, segnam, dtint2, sdata FROM edid4 WHERE docnum = '00000000002048xx' ORDER BY segnum
-- ✅ calisir   (JOIN icinde de calisir: edid4 ~ edidc, credat filtresiyle)
SELECT * FROM edid4 ...                     -- ⛔ 400
SELECT segnum, segnam, sdata FROM edid4 ... -- ⛔ 400  (DTINT2 yok)
SUBSTRING( sdata, 1, 20 )                   -- ⛔ 400  (LCHR SQL ifadesinde kullanilamaz)
```

**Alanlara kesmek için offset kaynağı:** `<musteri-d>_cpi_delfor/gen/segfields.json` (canlı `EDSAPPL`'den
türetilmiş; `{pos, name, rollname, leng}`). Örn. `E1EDP16` = `ETTYP(1)·PRGRS(1)·EDATUV(8)·EZEIT(4)·
EDATUB(8)·ETVTF(2)·…` ⇒ ham `" D20260914    20260914  240"` birebir oturur.
⚠ `EDSAPPL`'i SQL ile sorgularken kolon adlarını tahmin etme (`extlen`/`offset` **yok** → 400);
yerel `segfields.json` zaten canlıdan üretilmiş, önce ona bak.

**Why:** Bu, 2026-08-19'da bir kez ölçülmüştü (`governance/infra-findings.md`) ama **yalnız kuyruk
dosyasında** kaldı — kuyruk bir hatırlama yüzeyi değildir. O kaydın kendi aksiyon maddesi
*"tarif `core/playbook/adt-*.md`'ye girsin"* **hiç yapılmadı** (ölçüldü 2026-08-28: `core/playbook`'ta
`DTINT2`/`SDATA` 0 eşleşme). Sonuç: aynı gün *"SDATA okunamaz, `IDOC_READ_COMPLETELY` şart"*
yanlış teşhisi konmuş ve üzerine **bir SAP objesi yaratılmıştı** (`ZCL_SD000_GET_IDOCDATA`).
⇒ Tarif erişilebilir değilse **obje yaratmaya** kadar giden bir maliyet doğuruyor.

📌 Genel ders: **ADT 400'ü "araç bu tipi vermiyor" demek değildir** — sebep gövdededir ve genelde
*"yanlış biçim"*tir. Dört ayrı 400, dört ayrı biçim hatasıydı.

**How to apply:**
- Canlı IDoc doğrulaması gerektiğinde (mapping çıktısı kontrolü, alan hizalaması, muhatap
  segmentleri) **önce bu sorguyu dene**; Z obje yaratma/ARAMA yoluna sapma.
- Yapı kontrolü için `SDATA`'ya hiç gerek yok: `SELECT segnum, segnam, psgnum, hlevel FROM edid4`
  segment ağacını (hiyerarşiyi) verir ve **filtresiz çalışır**.
- Uzun `WHERE`/`IN` listeleri `adt_sql_query`'de 400 üretebiliyor ⇒ tek `docnum` ile sor,
  toplu iş için `JOIN` + `GROUP BY` kullan.

İlişkili: [[feedback_sap-yazma-hatasi-once-known-errors]] · [[feedback_arac-basarisizligini-zararsiz-sayma]] ·
[[feedback_kural-gate-lenmeli-yoksa-anlamsiz]] (kayıt kuyrukta kalırsa ≈ kayıtsız) ·
[[project_zsd001-teslimat-plani-edi-idoc]]

Son-doğrulama: 2026-08-28 — 53 canlı DELFOR02 IDoc'unun segment ağacı + `E1EDKA1`/`E1EDP10`/`E1EDP16`
içerikleri bu yolla okundu (Z sınıfı kullanılmadı).
Applies-to: S/4 private · IDoc doğrulaması gereken her tur
