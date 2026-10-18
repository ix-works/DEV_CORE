---
name: ambalaj-talimati-coklu-p-eml-yaratamaz-vhupo-fm
description: "Ambalajlama talimatı (PI) yaratma: A_PackingInstruction EML/OData ≥2 P kalemli talimatı yaratamaz (VHU01/029); VHUPO_PACK_INSTRUCTION_CREATE çalışır ama PROP_PIKP_IMP zorunlu, yetki denetlemez, test modunda tampon reçetesi ister"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: eb086373-3ff5-4f0b-9566-83527256cc5a
  modified: 2026-09-28T19:27:48.539Z
---

S/4 private'ta ambalajlama talimatını **programdan** yaratırken:

- **EML `A_PackingInstructionHeader`/OData `API_PACKINGINSTRUCTION` ≥2 `P` (ambalaj) kalemli talimatı yaratamaz** → `VHU01/029 Yükleme aracı olarak tek bir kalem tanımlanması gerekir`. Kök: `CL_LO_HU_PI_MANAGE->map_pi_components` yaratmada **her** P kalemine `indmapaco='X'` basar; A_ projeksiyonunda bu bayrağı taşıyan alan yok. (OData aynı BO handler'ından geçer — çağrısı ölçülmedi, kod yolu aynı.)
- **Çare: FM `VHUPO_PACK_INSTRUCTION_CREATE`** (FUGR VHUPO, notReleased — `balanced` clean-core'da std/10 ADIM 4 gerekçesiyle). Kurallar (FM kaynağı `CREATE_PACK_INSTRUCTION_NODIA` + canlı PoC):
  - `PROP_PIKP_IMP` **zorunlu** (OPTIONAL değil) — verilmezse dump `CALL_FUNCTION_PARM_MISSING`; boş yapı verilir.
  - Tam **1** kalemde `indmapaco` (yükleme aracı), onun miktarı **1** (`VHU01/042`), ≥1 ürün kalemi.
  - FM **yetki denetlemez** (`perform check_authority` yorum satırı) → program `AUTHORITY-CHECK OBJECT 'LO_HU_PI' ID 'ACTVT' '01'` yapar.
  - Mevcut numara: subrc **12** (`exsist`) ama mesaj yanıltıcı (`VHUPD/026`) → ayrımı subrc'ye dayandır.
  - Test modunda aynı oturumda "zaten var"ı önlemek: `ROLLBACK WORK` + `VHUPODB_PACKOBJ_REFRESH_BUFFER` + `VHUPO_REFRESH` (PoC'ta çalıştığı ölçüldü; mekanizma — FG global tamponu — HİPOTEZ).

**Why:** Bir projede, 2026-09-28: EML PoC'u tek-P'de MODIFY'ı kabul etti, çok-P'de 029 verdi; dosyadaki 95 talimat çok-P'liydi. FM PoC-2'de test + gerçek yaratma (DEV) başarılı, read-back + bağımsız SQL ile doğrulandı.

**How to apply:** PI toplu yükleme/yaratma işinde API seçimini baştan FM'e kur; yukarıdaki dört kuralı tasarıma yaz. EML'i yalnız tek-P senaryosu garantiyse düşün. Tüketim tarafı ayrı: core `standards/09-packing-instruction-consumption.md`.

Son-doğrulama: 2026-09-28 — FM kaynağı + PoC-1 (EML, ROLLBACK) + PoC-2 (FM, DEV gerçek yaratma) + kullanıcı testi 22/22
Applies-to: s4_private (2025); diğer profillerde ölçülmedi
prior-art: yok (memory + core standards/09 PI tüketim — yaratma yok) · kaynak: vaka projesinin paket günlüğü + TS (tüketici repoda)
