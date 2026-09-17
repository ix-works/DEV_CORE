---
name: feedback_empty-key-tabloda-olcutsuz-sort
description: "WITH EMPTY KEY tabloda BY/COMPARING'siz SORT ve DELETE ADJACENT DUPLICATES: dayanacak anahtar yok — ATC 'check the semantics' der, yerel kapı YOK"
metadata:
  type: feedback
---

`TYPES … WITH EMPTY KEY` bir tabloda **ölçütsüz** `SORT itab.` ve `DELETE ADJACENT DUPLICATES
FROM itab.` **birincil anahtara** dayanır — ve o anahtar **boştur**. SAP'nin kendi ATC'si:
*"is a table with an empty primary key. **Check the semantics of the statement.**"*

⚠ **Şiddet bağlama bağlı, tek tip değil:**
- Sıralama bir **doğruluk kuralıysa** (ör. kilitleri artan sırada alma = deadlock önleme) ⇒ kural
  sessizce delinmiş olabilir. (`ZSD001` `ZCL_SD022_LOG.LOCK_MATERIALS`, K-4)
- Sıralama+dedup yalnız bir `FOR ALL ENTRIES` girdisi hazırlıyorsa ⇒ IN-listesi büyür ama sonuç
  değişmez; etki **verimlilik**. (`ZSD000` `ZCL_SD015_BOOKING_API`, 3 yer — canlı ATC ile ölçüldü)

**Düzeltme her iki durumda da aynı ve güvenli:** ölçütü **açıkça** ver —
`SORT itab BY table_line ASCENDING.` · `DELETE ADJACENT DUPLICATES FROM itab COMPARING table_line.`
Belirsizliği kaldırmak tek başına yeterli gerekçedir; "bugün no-op muydu" sorusunu **ölçmeden**
koda yazma (ABAP koşturulamıyorsa iddia edilemez).

**How to apply:** `EMPTY KEY` gördüğün her yerde ölçütsüz `SORT`/`DELETE ADJACENT DUPLICATES` ara.
⛔ Yerel kapı YOK — kusur ancak kod SAP'ye gidip ATC koşunca görünür (aday gate: `infra-findings`).
