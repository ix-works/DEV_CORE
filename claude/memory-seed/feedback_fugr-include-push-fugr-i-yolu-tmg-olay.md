---
name: feedback_fugr-include-push-fugr-i-yolu-tmg-olay
description: "Fonksiyon grubu include'u (SE54 TMG olay include'u gibi) programs/includes yolundan yazılamaz (403 TK 103) — functions/groups/<fg>/includes/<incl>; TMG olay 01 iptal deseni S DISPLAY LIKE 'E' + vim_abort_saving"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: b1b58519-2c91-4830-aeab-6f0c875a0510
---

**Fonksiyon grubunun içindeki include** programs/includes yolundan yazılamaz. Örnek: SE54'ün olay FORM'u için açtığı `L<FUGR>F01`. Yazım şu şekillerde patlar:
- `push_object --type include` ve `object_types` daima `/sap/bc/adt/programs/includes/<ad>` yoluna gider ve R3TR PROG kilidi ister. Sonuç: 403 `TK 103 "Nesne adı için sözdizim olanaksız"`.
- Bayat CSRF önbelleği bu hatayı çıplak "403" olarak maskeler.

**Doğru yol:** `/sap/bc/adt/functions/groups/<fg>/includes/<incl>`, tipi FUGR/I. Reçete:
1. lib `lock_object(FUGR/I URL, istek K)` → `set_object_source` → `unlock_object`.
2. `activate_object(include URL)`.
3. Sonuç ne olursa olsun şunları ölç:
   - aktif kaynak = yerel (rstrip-md5);
   - ana programda `INCLUDE` satırı duruyor;
   - TVIMF satırı yerinde;
   - inaktif 0.

Ölçmenin sebebi: başarısız dönen bir FUGR aktivasyonu bir kez FUGR/I'yi düşürmüştü. Araç kusurları (include türünün bu yolu bilmemesi) ilk temasta tüketici projenin kuyruğuna yazıldı.

**TMG olay 01 mekaniği (SAP kaynağından ölçüldü):**
- Çağrı yeri `LSVIMF14`, iptal koşulu `sy-subrc <> 0 OR vim_abort_saving`.
- `<ACTION>` sabitleri `LSVIMDAT`: N/U/D/Y/X/' '.
- `<vim_total_struc>` ve `<action>` alanları `LSVIMF44`'te `total` başlık satırına bağlanır.
- İptal deseni: `MESSAGE s… DISPLAY LIKE 'E'` + `vim_abort_saving = abap_true` + `sy-subrc = 4`. `MESSAGE e` kullanılmaz, çünkü olay PAI'de koşar.
- Çalışan emsal tüketici projede durur (`<source_root>/<MODULE>/<PKG>/functions/L<FUGR>F01.prog.abap` biçimi + paketin TS'inde olay bölümü); yeni projede emsal yoksa yukarıdaki dört madde iskelettir.

**Why:** İlk temasta playbook'ta ne yol ne olay emsali vardı. Kök sebebi bulmak iki probe gerektirdi.
**How to apply:** Fonksiyon grubu include'u yazılacaksa gateway brifine FUGR/I yolunu ve 4 ölçümü yaz. TMG olay kodu yazılacaksa yukarıdaki iptal desenini ver.

Son-doğrulama: 2026-10-30 · Applies-to: s4_private (ADT), Z FUGR / SE54 TMG olayları
prior-art: kısmen — [[feedback_adt-include-objesi-prog-tipiyle-404-sahte-negatif]] (okuma tarafı); FM sıkı-lock reçetesi core `playbook/adt-fugr-functions.md`
