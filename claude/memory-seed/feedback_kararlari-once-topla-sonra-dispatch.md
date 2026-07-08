---
name: feedback_kararlari-once-topla-sonra-dispatch
description: "Build-unit'in tüm user-kararlarını önce tek tek topla, sonra ajana konsolide yönerge"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 791c30b9-6728-4e20-94d7-8d4a14484d2d
---

Kullanıcı (2026-06-14) iş akışı kuralı koydu: **bir build-unit'e başlamadan önce o unit'in TÜM user-kararlarını tek tek sor + topla; ANCAK ondan sonra ajana tek konsolide, tam-kararlı yönerge ver.**

**Why:** "karar→dispatch→ajan mid-build yeni açık-nokta bulur→tekrar kullanıcıya sor→tekrar dispatch" deseni çift yönlü ping-pong (hem kullanıcı hem ajan round-trip'i + patinaj). Kararları front-load etmek bunu eler.

**How to apply:** Açık-noktalar recon'dan çıkıyorsa: önce recon (salt-analiz) → çıkan user-kararlarının HEPSİNİ tek tek sor + topla → sonra build dispatch (konsolide). Teknik/lead-kararlarını ayır (onları ben veririm), yalnız gerçek user/iş-kararlarını sor. [[feedback_tek-soru-ve-bagimsiz-dokuman]] (tek tek sor) ile birlikte: soruları tek tek ama HEPSİNİ dispatch'ten önce. Kanonik: [[governance/agent-teams-operating-model]] §4.
