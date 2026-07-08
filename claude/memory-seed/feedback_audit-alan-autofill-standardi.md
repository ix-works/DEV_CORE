---
name: audit-alan-autofill-standardi
description: Tabloda audit alanı (created/updated by-date-time) varsa AI otomatik doldurur — idempotent setAdmin det; her geliştirmede operatöre kural teyidi
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 08868cc7-ead9-4d38-b6fe-2fd1fd3eb04c
---

Her RAP backend geliştirmesinde, tabloda `created_by/create_date/
create_time/updated_by/update_date/update_time` (veya muadili) audit
alanları varsa **AI bunları otomatik doldurur** — kullanıcı ayrıca
istemese bile (kullanıcı talimatı 2026-05-19).

**Kural (operatöre her geliştirmede teyit ettir):** create → created_*
VE updated_* (hepsi); sonraki update → SADECE updated_*; created_*
asla değişmez. Aynısı composition child için de.

**Mekanizma (KANITLANDI, kanonik = ORDER ZCL_SD001_ORDER.ccimp):**
idempotent `setAdmin` determination — BDEF root+child `determination
setAdmin on save { create; update; }`; handler `READ ... CreatedBy`
boş=yeni→6 alan, dolu=update→3 alan; **instance `DATA mt_done`
guard** (LUW-scope, 2. pas'ta CONTINUE) cyclical-on-save dump'ı kırar;
`IN LOCAL MODE` + `UPDATE FROM %control`.

**Why:** Excel/list'te audit alanları boş + `PT0H0M0S` görünüyordu.
Guard'sız determination "Infinite loop ... cyclical triggering of
on-save determinations" dump verir; `with additional save` early
numbering'de create component'i boş bırakır. İdempotent guard tek
sağlam yol.

**How to apply:** Yeni programda DDIC audit alanlarını tespit et,
operatöre kuralı teyit ettir, kanonik pattern'i kopyala-uyarla. Edm.Time
alanları UI `sap.ui.model.odata.type.Time` + export `EdmType.Time`
(personalizer kind `'time'`). Standart: standards/05 §9A; pattern:
playbook/ui-backend-rap.md §F; adt-rap.md §32.6i SUPERSEDE; checklist
BE-AUDIT-01. Bağlı: [[feedback_liste-ekrani-alv-standardi]] · [[feedback_freestyle-ui-preflight]].
