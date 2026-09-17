---
name: feedback_privileged-access-strict-mode-into-sonda
description: "WITH PRIVILEGED ACCESS kullanan ABAP SQL SELECT'te INTO klozu SELECT'in en sonunda olmalı (strict mode)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 2162678c-4758-4542-82c8-c17265c98eee
---

`WITH PRIVILEGED ACCESS` (released CDS entity'yi yetki kontrolünü atlayarak okuma) eklenen bir ABAP SQL
`SELECT`, ABAP SQL **strict mode**'a girer. Strict mode'da `INTO`/`INTO TABLE`/`APPENDING` klozu
**SELECT'in en sonunda** olmak zorundadır — `WHERE`'den önce yazılamaz (klasik ham tablo SELECT'lerinde
serbest olan sıra burada geçmez).

**Why:** ZSD001_CLC / `ZCL_SD022_PRECHECK` içinde KNA1/KNVV/KNVP ham SELECT'leri released CDS'e
(I_Customer/I_CustomerSalesArea/I_CustSalesPartnerFunc) `WITH PRIVILEGED ACCESS` ile migre edilirken
`INTO` eski alışkanlıkla `WHERE`'den önce bırakıldı ⇒ 3× aktivasyon-öncesi syntax hatası
("The INTO/APPENDING clause must be at the end of the SELECT"). Gateway fail-closed davrandı (kaynak
yükledi, aktive etmedi) — hata canlıya sızmadı ama bir push turu boşa gitti. Emsal doğru kalıp:
`ZCL_SD015_BOOKING_API.clas.abap:587-591` (SELECT alanlar → FROM ... WITH PRIVILEGED ACCESS → WHERE →
INTO, bu sırayla).

**How to apply:** `WITH PRIVILEGED ACCESS` eklenen/migre edilen her SELECT'te push ÖNCESİ INTO'nun konumunu
kontrol et — SELECT alanlar → FROM ... WITH PRIVILEGED ACCESS → WHERE → INTO sırası. [[feedback_kapi-zinciri-derlemeyi-gormez]]
ile aynı sınıf: kapı zinciri (`check_abaplint`, `check_syntax` KAPALI) bu hatayı görmez, ilk derleme
otoritesi gateway'in syntax-check'idir.
