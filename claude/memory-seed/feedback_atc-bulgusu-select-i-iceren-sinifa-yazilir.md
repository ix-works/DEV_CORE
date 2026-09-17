---
name: feedback_atc-bulgusu-select-i-iceren-sinifa-yazilir
description: "ATC 'nested DB read' bulgusu DÖNGÜYÜ içeren sınıfa değil, SELECT'i içeren sınıfa yazılır — baseline'ı orada ara"
metadata:
  node_type: memory
  type: feedback
---

ATC'nin *"NonLocal Nested Reading DB OP"* ailesi (`3C9E0BF48BA22224184025A0C7C6C04B`) bulguyu
**döngüyü yazan sınıfa değil, `SELECT`'i barındıran metodun sınıfına** yazar.

**Why:** 2026-09-16'da `ZCL_SD022_PROCESSOR`'ın 11 P1 bulgusunun **11'i de** kendi içindeki
`READ_CHAIN_STATE` (×6) · `REDO_FROM_STEP` (×3) · `CREATE_INVOICE` (×1) metotlarındaydı.
Döngüyü başka bir sınıfa (bir behavior ccimp'ine) taşımak bulguyu **taşımaz**; çağrılan
metot yeni bir döngüden çağrıldığında bulgu **çağrılanın** sınıfında **artabilir**.

**How to apply:**
1. Döngü-içi çağrı eklerken baseline'ı **çağıran sınıfta değil, SELECT'i içeren sınıfta** ölç.
2. Push öncesi o sınıfın bulgu sayısını yaz, push sonrası **aynı ölçümü tekrarla**; artış yoksa
   bunu ayrıca beyan et. ATC push'lanmamış kaynağı ölçemez ⇒ önce/sonra kıyası **gateway'in işidir**.
3. Baseline'ı build sırasında oku: var olan bir bulgu deseni (ör. `TYPES` önündeki `"!` ABAP Doc)
   yeni kodda **tekrarlanmayarak** bulgu doğması önlenebilir.

Son-doğrulama: 2026-09-16 · Applies-to: SAP ATC (s4_private, 2025)
İlgili: [[feedback_atc-priority-1-zorunlu]] · [[feedback_clean-core-released-cds-proaktif]]
