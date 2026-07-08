---
name: feedback_lider-build-yapmaz-experte-dagit
description: "Lider substantive feature build'i kendi inline yazmaz; frontend/backend-expert'e dağıtır (\"context bende\" rasyonalizasyonu meşru değil)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 6b9195f9-e63c-4781-931d-b9672c867a85
---

Kullanıcı 2026-06-18'de ("yine herşeyi sen yaptın, teams agent kullanmadın") lider'in ZSD001'de 3 küçük özelliği (FE #1/#3 + #2'nin FE'si + #2 backend ABAP) kendi inline yazmasını, sadece sonda bug-expert spawn etmesini eleştirdi. "yine" = tekrar eden tuzak.

**Kural (ADR 0018 işletim modeli):** Substantive FE/BE feature build = **frontend-expert / backend-expert** yapar; lider **orkestre eder** (recon → kararları topla → dispatch → bug-gate → gateway). Trivial mekanik düzeltme/konuşma turu = lider solo OK. Kullanıcı "solo" derse de lider solo.

**Why:** "Recon'da context'i topladım, inline daha hızlı" = modelin uyardığı tam rasyonalizasyon ([[feedback_arac-kod-fix-lider-isi]] mantığıyla aynı: dar lane disiplini). Sert gate'ler (gateway tek-yazıcı, bug-expert) tutsa bile expert-build katmanı atlanırsa context-izolasyonu + bağımsız uzmanlık + denetlenebilir iş bölümü kaybolur. Kullanıcı takımın kullanıldığını görmek istiyor.

**How to apply:** Çok-dosya/çok-katman feature işi gelince ÖNCE kararları topla ([[feedback_kararlari-once-topla-sonra-dispatch]]), SONRA frontend-expert + backend-expert'e scoped dispatch et ([[feedback_subagent-karar-kurali]]). Lider kod yazmaya başlamadan "bu expert işi mi?" diye dur. Build bitince → bug-expert gate → adt-gateway SAP yazımı. İlgili: [[project_agent-team-td-agent-teams]] · [[feedback_dosya-bolgeleri-yazim-yetkisi]] (Zone B lider'e izin verir AMA operating-model expert-build bekler).
