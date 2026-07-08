---
name: feedback_deploy-lokal-test-onayi-sart
description: "SAP'e (BSP/UI) deploy ETME — kullanıcı lokal testi \"OK\" demeden; deploy kullanıcı-kapılı"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: cbd3c1b7-21b6-433c-9916-4307c1ea6587
---

Kullanıcı kuralı (2026-06-19): **Lokal test bitmeden SAP'e deploy etme.** Build → bug-gate → **lokal sun** → kullanıcı test eder → "OK" der → SADECE O ZAMAN gateway deploy. Otomatik/proaktif deploy YASAK (lider Wave-1'i kullanıcı onayı almadan deploy etti → uyarı geldi).

**Why:** Freestyle UI5 lokal sunucu (8101) zaten CANLI backend'i tüketir → kullanıcı FE değişikliğini lokalde gerçek veriyle test edebilir; deploy gereksiz ve erken (yanlışsa canlı BSP'yi kirletir). Test sahibi kullanıcı; deploy onayı onun.

**How to apply:**
- FE build (pas) bitince: bug-gate → **lokalde sun** (npm start / 8101) → kullanıcıya "lokal hazır, test et" de → BEKLE. "OK/deploy et" gelene kadar gateway'e UI deploy görevi VERME.
- **BE-bağımlı FE özelliği** (yeni CDS alanı: KDMAT/ağırlık vb.) lokal testte ancak BE CDS canlıda AKTİF ise görünür ($metadata canlıdan gelir). Bu durumda BE-aktivasyonu lokal-testin ÖN-KOŞULU → kullanıcıya AÇIKLA + onay iste (BE-aktivasyon da SAP-yazımı; ayrı karar). Salt-FE değişikliği (BE-bağımsız) için BE-aktivasyon gerekmez.
- "done/deploy" demeden runtime-doğrula prensibiyle ([[feedback_done-tam-kapsam-dogrula]], [[feedback_ui5-v2-plumbing-reuse-traps]]) tutarlı: fark = doğrulamayı KULLANICI lokalde yapar, deploy onun onayına bağlı.
- İlgili: [[feedback_ui-deploy-noninteractive]] (deploy NASIL yapılır — ama NE ZAMAN = kullanıcı OK'i), [[feedback_lider-bloke-olmama-background-dispatch]].
