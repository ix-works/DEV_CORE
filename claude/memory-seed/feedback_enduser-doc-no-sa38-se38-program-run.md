---
name: feedback_enduser-doc-no-sa38-se38-program-run
description: Son kullanıcı dokümanında SA38/SE38/SE80 ile program çalıştırma ASLA önerilmez; erişim yoksa yöneticiye yönlendir
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b7b38961-86df-4b41-afd7-f5fac2dce4f0
---

Son kullanıcı dokümanlarında (KD, in-app help, GUI F1/DOCU) **SA38/SE38/SE80 ile programı çalıştırma** bir erişim yolu olarak ASLA verilmez — ne ana yol ne "alternatif/yedek".

**Why:** Hiçbir son kullanıcı SA38/SE38 gibi geliştirici/yönetici transaction'larını çalıştıramaz/çalıştırmamalı. Kullanıcı işlem koduna (tcode) erişemiyorsa bunun bir sebebi vardır (yetki kasıtlı verilmemiştir) → workaround sunmak yanlış + güvenlik/yetki modeline aykırı. Kullanıcı 2026-06-30, ZSD001 F1 pilotunda gördü ("İşlem koduna erişiminiz yoksa SA38 ile program ... çalıştırılır" cümlesi).

**How to apply:**
- Erişim cümlesi = yalnız atanmış **tcode** (örn ZSD001) veya **menü/rol**. tcode yoksa: "kurumunuzca tanımlanan menü/rol üzerinden açılır."
- Erişim yoksa: "işlem kodunu göremiyorsanız erişim yetkisi tanımlanmamış olabilir — **sistem yöneticinize/yetkilinize başvurun**." (SA38/SE38 ÖNERME.)
- Tcode'u olmayan rapor (ör. ZSD000): dev-belirsizliğini son kullanıcıya yansıtma; generic menü/rol + yöneticiye yönlendir.
- **İstisna:** FS/TS gibi TEKNİK dokümanlarda geliştirici-bağlamı SE38 (ör. "transport öncesi program aktif mi SE38") meşru — son kullanıcı erişim yolu DEĞİLse kalır. Ama FS/TS'te "erişim noktası: SA38→program" tarzı KULLANICI-erişim çerçevesi de temizlenir.
- İlgili: [[feedback_tek-soru-ve-bagimsiz-dokuman]] · standards/08-classic-gui-f1-help (ONKOSUL/Yetki bölümü) · standards/04. Bu kural gate'lenmeli (yoksa fan-out'ta tekrar sızar) — [[feedback_kural-gate-lenmeli-yoksa-anlamsiz]].
