---
name: feedback_behavior-pool-main-empty-ccimp-trap
description: "Managed behavior pool source/main DAİMA boş; handler'lar CCIMP'te — \"boş pool → validasyon çalışmıyor\" sahte-flag tuzağı"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 968d8d8f-00ae-498a-9770-6e066dc35c46
---

RAP **managed behavior pool** sınıfının `source/main` include'u DAİMA boştur (`PUBLIC ABSTRACT FINAL FOR BEHAVIOR OF ...` + boş gövde, ~159 byte) — bu NORMALDİR. Tüm validation/determination/action handler'ları **CCIMP** (`includes/implementations` URI) içindedir.

**Tuzak:** Yalnız `adt_get` ile pool'un main'ini okuyup "sınıf boş → BDEF'te bildirilen validasyonlar çalışmıyor / kurallar UI buffer'da kalmış" sonucuna varmak. MCP `adt_get` bir behavior-pool class için yalnız main include döndürür; CCIMP ayrı çekilir.

**Why:** 2026-06-24 doküman-tazeleme statik analizi `ZCL_SD001_SEVKEMRI`'yi "tamamen boş" sanıp fittings_se validasyonlarını "çalışmıyor" diye flag'ledi (false-positive). Canlı CCIMP raw GET ile 10.472 byte DOLU çıktı; `validateItems on save` → `lhc_SevkEmriItem.validateItems` → `factory=>get_strategy()->validate_items` zinciri sunucu-otoriter çalışıyordu. Bir spekülatif blocker'a boşa mesai harcandı (bkz. [[feedback_dogrula-once-flag-spekulatif-blocker-yasak]]).

**How to apply:** RAP behavior/validation wiring incelerken behavior pool'u "boş" ilan etmeden ÖNCE CCIMP'i (implementations include) çek. BDEF bildirimi (`validation/determination/action`) ↔ CCIMP'teki `lhc_*` lokal metot 1:1 eşle; eşleşme varsa wiring sağlamdır. "main boş" = kanıt DEĞİL. İlgili: [[feedback_resolved-tooling-bugs]] · [[feedback_arac-basarisizligini-zararsiz-sayma]].
