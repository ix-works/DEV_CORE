---
name: feedback_generic-tool-program-spesifik-isim-verme
description: "Generic/reusable bir araca (FM, FG, class) program-spesifik isim verme; container/isim aracın amacını yansıtmalı"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c874b6ce-b5f4-4780-8a44-b99611c71492
---

Kalıcı, yeniden-kullanılabilir bir araç objesi (FM, function group, class, vb.) yaratırken, onu ilk kullanan programın/işin adıyla DEĞİL, aracın **kendi generic amacıyla** isimlendir. Container'ı (ör. FM'in function group'u) da aynı şekilde aracın amacını yansıtmalı.

**Why:** C1'de ekran-üreteci `ZSD000_FM_SCREEN_GEN`'i, ilk hedefi SIL programı olduğu için yanlışlıkla `ZSD000_FG_SIL` (program-spesifik) function group'unda yarattım. FM generic bir araç; FG'si `ZSD000_FG_SCREEN_GEN` olmalıydı. Kullanıcı yakaladı: "_SIL değil ZSD000_FG_SCREEN_GEN olmalıydı". Düzeltme pahalıydı: FM adı SAP'de global benzersiz → yeni FG yarat + eski FM sil + yeni FG'de yeniden yarat+push+activate + eski FG sil (+ RFC-enable sıfırlandı).

**How to apply:** Reusable bir obje yaratmadan ÖNCE isim sor: "bu sadece bu program/iş için mi, yoksa araç mı?" Araçsa generic ad ([_SCREEN_GEN], [_UTIL], [_ALV] gibi) + uygun container. Program-spesifik objeler (report, o işe özel class) program adını taşıyabilir. Naming standardı: [[feedback_done-tam-kapsam-dogrula]] gibi — baştan doğru isim, sonradan taşıma maliyetli.
