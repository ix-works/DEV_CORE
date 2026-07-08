---
name: feedback_klasik-program-include-bol
description: "Klasik ABAP program tüm kodu tek REPORT body'sinde TUTMAZ; include'lara bölünür (TOP/CLS/O01/I01/F01) — yeni klasik program yazınca BAŞTAN böl"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c874b6ce-b5f4-4780-8a44-b99611c71492
---

Yeni bir klasik ABAP programı (report / module pool / Dynpro) yazarken **tüm kodu tek REPORT body'sine KOYMA**. Kod include'lara bölünür; main program sadece `INCLUDE` ifadeleri + event blokları (`START-OF-SELECTION`, `INITIALIZATION`...) içerir.

**İsimlendirme (kullanıcı kararı 2026-06-03):** include = programın `_P_`'si yerine `_I_` (Include) + tip-suffix `_<X>01`:
- `ZSD<pkg>_I_<PRG>_T01` (TOP) — TABLES/TYPES/DATA/CONSTANTS/SELECT-OPTIONS/CLASS DEFINITION
- `_C01` (CLS) — CLASS IMPLEMENTATION (LCL_*)
- `_F01` — FORM rutinleri
- `_O01` — PBO modülleri (MODULE ... OUTPUT)
- `_I01` — PAI modülleri (MODULE ... INPUT)
- `_S01` — selection-screen events (opsiyonel)
- Tip harfi T/C/O/I/F/S, sıra no 01 (büyük include → 02...). Include'lar **INCLUDE objesi (PROG/I)** olarak yaratılır, standalone program değil. Repo: `programs/includes/`.

**Why:** Kullanıcı bunu projenin EN BAŞINDA söylemişti ve standardı (std 06 §1) belirlemiştik; ben uzun oturumda klasik programları (ZSD000_P_ALV_TEMP1/2/3) tek-body yazdım → kullanıcı hatırlattı: "include'lara bölünmeli, _CLS/_TOP standardımız vardı." Tek-body klasik program = standart ihlali.

**How to apply:** Yeni klasik program işine başlamadan `standards/06-coding-classic-dialog.md` §1'i oku; main'i INCLUDE + event'lere indir, kodu T01/C01/O01/I01/F01 include'larına dağıt (ADT'de PROG/I objeleri yarat). NOT: mevcut `ZSD000_P_ALV_TEMP1/2/3` şablonları kasıtlı tek-body bırakıldı (sadece ALV/screen-gen deseni gösterir, yapı örneği değil) — onları örnek alma. Ekran/status üretimi: [[project_dynpro-gui-status-uretici]]; ALV inline: [[feedback_klasik-alv-template-first]].
