---
name: feedback_timeout-rg-shim-sessiz-sifir
description: "Kabukta `timeout <n> rg … 2>/dev/null` SESSİZCE boş döner — rg bir shim, timeout onu exec edemez (rc=127) ve hata stderr'le yutulur; boş arama sonucu bir hüküm değildir"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: cca08bdf-c505-460c-a1ba-8d1635bd8f7c
---

Bu kabukta `rg` PATH'te gerçek bir çalıştırılabilir değil, shim/fonksiyon (`which rg` → yok, `rg --version` → çalışır). `timeout 60 rg …` → `timeout: failed to run command 'rg'` rc=127; `2>/dev/null` eklenmişse geriye **boş çıktı** kalır ve "eşleşme yok" ile "komut hiç koşmadı" ayırt edilemez.

**Why:** 2026-08-28 (Q197) — bu komutla "koda referansı 0" hükmü kuruldu, merge edilmiş bir core PR gövdesine yazıldı ve az kalsın git-tracked bir dosya silinecekti; aynı soru `find | xargs grep` ile 18 dosya verdi.

**How to apply:** Arama için harness `Grep` aracını kullan (kontrol grubunda doğru sonuç verdi). Kabuk `rg` gerekiyorsa `timeout` ile sarma ve `2>/dev/null` ekleme. Boş sonuca dayanan her "yok / 0 referans" hükmünden önce bilinen-pozitif bir desenle aynı komutun ÇALIŞTIĞINI göster. Bkz. [[exit0-degil-cikti-kaniti]] · [[hook-negatif-test-exit0-iki-anlamli]].

Son-doğrulama: 2026-09-13
Applies-to: Windows Git Bash oturumunda liderin kabuk aramaları

---
**Son-dogrulama:** 2026-09-13 (ders yazim tarihi — o gunden beri YENIDEN OLCULMEDI) · **Applies-to:** bu cekirdegi kullanan tum projeler

⚠ **ARAC IDDIASI** — bu ders *"bugun su arac/kapi boyle davraniyor"* der, yapisal bir olgu
degil. Arac surumu degismis olabilir: davranisa **dayanmadan once bir kez olc**. (Vaka: bir
kardes ders, dayandigi kusur duzeltildikten sonra 3 hafta bayat yasadi; tohuma alinmadan
once olculup elendi.)
