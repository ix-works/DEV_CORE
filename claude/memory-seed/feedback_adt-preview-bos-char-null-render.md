---
name: feedback_adt-preview-bos-char-null-render
description: "ADT data-preview boş CHAR'ı `null` render eder — SQL NULL DEĞİL. Kanonik: core/playbook/adt-cds.md T13."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c9f6971e-7b33-4e0d-8953-9e226b56c2bf
---

**KANONİK: `core/playbook/adt-cds.md` → T13** (2026-07-28'de yazılmış, kapsamlı: üç-değerli mantık etkisi,
`IS NULL` vs `= ''` ölçümü, ve `adt_sql_query` 400-sınırları).

Özet: `adt_sql_query` çıktısında `null` görünen CHAR kolon **boş (spaces)** olabilir. NULL'lığı ekrandan
okuma, **`count(*) WHERE col IS NULL` ile ÖLÇ**.

⚠ **Bu ders 2026-08-10'da NÜKSETTİ** — lider `null` render'ını veri sanıp ajana "kanıt" diye verdi ve
`is not null` guard'ı yazdırdı; bug gate ölçümüyle çürütüldü (`IS NULL` → 0 satır). Kayıt vardı, okunmadı.
**Aynı gün ikinci nüks:** T13'ün belgelediği `adt_sql_query` 400-sınırı da sıfırdan yeniden keşfedildi.
📌 Tanıdık semptomda **önce `adt-cds.md`'yi ara** — bu dosya T1-T14 tuzak bankasıdır.

Son-doğrulama: 2026-08-10 (nüks vakası) · Applies-to: `adt_sql_query`/data-preview kullanan her ölçüm
İlgili: [[feedback_dogrulama-sezgileri-dort-kural]] · [[project_zsd001-bolum-tanimi-coklu-pb]]
