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

**GENİŞLETME 2026-08-13 — aynı kural TEKNİK ŞARTLAR için de geçerli (iki kez ihlal edildi, ikisi de tur maliyeti):**
① *Kullanıcıya:* bir çözümün iki parçası varsa (fix + onun mümkün kıldığı otomatik hâli) ikisini **birlikte** sun. Yarısını sabah, öteki yarısını bir saat sonra getirdim; kullanıcı haklı olarak *"yeni mi çıktı, madem çözüyor neden yaptırmadın"* dedi. Sıralama teknik olarak zorunluydu (taban düzelmeden otomatik yol sessiz-ezme yapardı) ama **kapsamı** baştan görmesi gerekirdi.
② *Ajana:* şartı **brifingin İÇİNE** koy. Dispatch'ten sonra iletilen kısıt uygulanmayabilir ve ajan bunu raporunda *söylemeyebilir* (atomiklik şartını iki kez ilettim; ne uygulandı ne "uygulamadım" diye yazıldı — diff'i okumasam kaçacaktı). ⇒ **Dispatch öncesi mevcut kodu OKU**: bugün `materyalize`'in dizini silip yeniden kurduğunu baştan görseydim şart brifingde olurdu.
**Son-doğrulama:** 2026-08-13 · **Applies-to:** her subagent dispatch'i (infra/build fark etmez).
İlgili: [[feedback_done-tam-kapsam-dogrula]] · [[feedback_lider-ajan-paralel-yazim-cakismasi]]
