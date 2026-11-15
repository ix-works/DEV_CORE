---
name: feedback_read-entities-bo-disi-tamponu-gormez
description: additional save'de BO-dışı tabloya yazılacak satırlar READ ENTITIES ile görülmez — aynı istekte sayım/sıra hesabı DB ∪ kendi tamponun üzerinden yapılır
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

`managed with additional save` modelinde BO dışındaki tablolara (geçmiş, kuyruk, karar satırları gibi) `save_modified`'da yazılacak satırlar işleyicinin **kendi tamponunda** durur. `READ ENTITIES` yalnız BO varlıklarının işlem tamponunu okur, dolayısıyla bu satırları **görmez**. Aynı istekte "kaç karar verildi" ya da "sıradaki numara ne" hesabı `READ ENTITIES` ile yapılırsa, bu istekte yapılan yazımlar sayıma girmez.

**Why:** 2026-11-07'de bir doc-gate kapanış turunda yakalandı. Bir düzeltme onay seviyesi sayımını `READ ENTITIES` ile yapacak şekilde yazılmıştı, ama sayılan tablo BO dışındaydı. Doğru yol: DB `SELECT` sonucu ∪ kendi tampon (aynı anahtar varsa tampondaki satır DB'dekini ezer). Bu tasarım muhakemesidir; çalışma anında ölçülmedi.

**How to apply:** Bir RAP tasarımında sayım ya da numara kuralı yazmadan önce tablonun BO varlığı (persistent table) mı yoksa BO dışı mı olduğunu belirle. BO dışıysa kuralı "DB ∪ tampon" olarak yaz. Tablo BO dışından da (iş, başka işleyici) yazılıyorsa max+1 yerine UUID anahtar + zaman damgası sırası kullan. Tablo yalnız BO içinden ve kilit altında yazılıyorsa max+1 kalabilir.

Son-doğrulama: 2026-11-07 (tasarım) · Applies-to: RAP managed with additional save
