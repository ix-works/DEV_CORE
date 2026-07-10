---
name: feedback_tablo-yaratma-onay-gate
description: "DDIC tablo yaratmadan ÖNCE alan+data element tasarımını göster, açık onay al; onaysız create_table yasak"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9032e66e-45f9-47c0-af9b-23b771ffe0a7
---

Yeni DDIC tablo yaratmadan **ÖNCE** tasarımı kullanıcıya göster ve **açık onay** al; onaysız `create_table` YASAK (kullanıcı kuralı, 2026-06-08).

Gösterilecek: tüm alanlar + her alanın **data element'i** + key/uzunluk + delivery class/category.

**Why:** ZSD000_T_UIVAR'ı onaysız yarattım; client/abap.clnt + raw char60 alanlarıyla çıktı, kullanıcı düzeltti (MANDT DTEL, std data element'ler). Önceden tasarım onayı bu round-trip'i önler + DDIC standartlarına (std DTEL kullanımı) uyumu garantiler.

**How to apply:** create_table çağırmadan önce alan tablosu sun → onay bekle. Kurallar: (1) client alanı = `mandt : mandt` (DTEL **MANDT**), "client : abap.clnt" DEĞİL; (2) mümkün olan her alanda **mevcut standart data element** kullan (ör. variant adı → DTEL `VARIANT` CHAR14; kullanıcı → `xubname`; UUID → `sysuuid_x16`; timestamp → `timestampl`), raw `abap.char(n)`'den kaçın; (3) audit alanı varsa std §F determinasyon. DDIC tablo adı **max 16 karakter** (uzun olursa "daha kısa ad seç" 422). Kayıt: AGENTS.md §2 "Kullanıcıdan TEYIT" tablosu. İlgili: [[feedback_done-tam-kapsam-dogrula]] · [[project_zsd001-rap-reports]]
