---
name: ayni-hash-degil-olu-kod
description: "Kopya dosya silmeden önce REFERANS ölç — aynı hash'te olmak ölü olmak değildir"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e424a095-8518-4681-bef7-a113d21aa4c0
---

Çoğaltılmış bir yardımcı dosyayı (util/helper) silmeden önce **referansı ölç**, hash'e bakma.
Aynı içeriğe sahip olmak ile kullanılmıyor olmak **farklı şeylerdir**.

**Why:** 2026-07-29, <PAKET-B>'de `TablePersonalizer.js`'in 12 kopyası vardı; dördü birebir aynı
hash'teydi (`dsk_se`, `fih_se`, `fittings_se`, `sip_se`). "Aynı dosyadan 4 tane var, 3'ü fazla"
diye bakıp hash ailesini silmek `sip_se`'yi **kırardı** — o kopya gerçekten kullanılıyordu
(`ChangeSe.controller.js`, `sap.ui.require` ile). Ölü olan 3'tü ve bunu ancak referans taraması
söyledi.

**How to apply:**
- Ölçüt **referans**: dosyayı çağıran var mı? Hash yalnızca "birleştirilebilir mi" sorusunu yanıtlar.
- Tarama **tüm dosya türlerinde** yapılır (`.js` + `.xml` + `.json`), yalnız `.js` değil — çağrı
  bir view/manifest üzerinden de gelebilir.
- UI5'te çağrı **string yol** olabilir (`sap.ui.require(["…/util/X"], …)`) → sembol araması değil
  **metin** araması gerekir; import listesine bakmak yetmez.
- `dist/**` ve `node_modules` kapsam dışı — build çıktısı kaynağı temsil etmez.
- Silmeden sonra o app'ler **yeniden deploy edilir**, yoksa canlı ile kaynak ayrışır.
- Birleştirme (konsolidasyon) ayrı karardır: N farklı hash **N farklı davranış** olabilir; farkların
  kozmetik mi davranışsal mı olduğu ölçülmeden birleştirmek sessiz regresyon üretir.

İlgili: [[fix-oncesi-where-used-blast-radius]] · [[dogrulama-sezgileri-dort-kural]]
