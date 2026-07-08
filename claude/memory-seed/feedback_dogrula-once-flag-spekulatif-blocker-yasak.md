---
name: feedback_dogrula-once-flag-spekulatif-blocker-yasak
description: "Ajan, doğrudan canlı-okumayla test edilebilen bir iddiayı doğrulamadan BLOCKER/FLAG yapıp eskale etmemeli (spekülatif blocker = false-positive)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: cbd3c1b7-21b6-433c-9916-4307c1ea6587
---

backend-expert (EWM stok build'inde) iki **BLOCKER-düzeyi FLAG** kaldırdı: (1) "I_EWM_PhysStockProd SDM bitmeden veri dönmez — sdm_proc_status ilk 100 satırında sınıfı bulamadım, doğrulayamadım" · (2) "TESLIMAT staging quant'ı EWMLocationType='B' filtresiyle fiziksel-view'a girmeyebilir". Lider **doğrudan okuyunca İKİSİ DE ÇÜRÜDÜ** (view 121 satır döndü → SDM bitmiş; 51-parti TESLIMAT/100 ST view'da VAR). Kullanıcı: **"çürüyen bir şeyi ajan neden BLOCKER yaptı, incele + tekrar etmesin diye encode et."**

**Kök sebep:** Ajan **dolaylı/varsayımsal** kontrol yaptı (sdm_proc_status'un parçası + filtre-mantığından çıkarım) ve büyük dump'ta "doğrulayamadım" deyip **lider'e eskale etti** — oysa **doğrudan test basitti** (view'ı OKU → veri dönüyor mu; partileri grep et). Tool çıktısı zaten "büyük çıktı dosyaya kaydedildi → grep et" tekniğini söylüyordu; ajan kullanmadı. = "tahmin yasak, canlı doğrula" ihlali.

**Why:** Spekülatif blocker = false-positive → lider zamanı (her birini lider doğruluyor) + güven kaybı (gerçek blocker'lar da şüpheli görünür). Doğrulanabilir bir şeyi doğrulamadan eskale etmek, doğrulama yükünü lider'e yıkmaktır.

**How to apply (encode edildi 2026-06-19 — 3 agent prompt'u: backend-expert/sap-research/bug-expert "DOĞRULA-ÖNCE-FLAG"):**
- Bir FLAG/BLOCKER yalnız **canlı-doğrulanmışsa** raporlanır. **Doğrudan canlı-okumayla test edilebilen** iddia (view veri dönüyor mu? kayıt/parti var mı? alan dolu mu? SDM→satır dönüyor mu?) → DOĞRULAMADAN BLOCKER YAPMA, önce DOĞRUDAN OKU.
- **Büyük-tablo dump'ı token-taşarsa:** çıktı dosyaya kaydedilir → `grep`/`Read offset` ile tara (tool çıktısı söyler). "giant dump, doğrulayamadım" geçerli mazeret DEĞİL.
- Dolaylı/varsayımsal (annotation/filtre okuyup "muhtemelen boş") YETMEZ; doğrudan test mümkünken onu yap.
- "Doğrulayamadım" yalnız **gerçekten imkânsızsa** → o zaman bile **BLOCKER değil**, "lider canlı-doğrulamalı" **düşük-severity not**.
- İlgili: [[feedback_reviewer-checklist-vs-wired-validator]] (reviewer PASS'e körü körüne güvenme — bu tersi: BLOCKER'a da körü körüne güvenme), [[feedback_arastir-once-patinaj-uretim-gorev]] (kanıtlı yöntem), bug-expert "FLAG-ÖNCESİ 4-SORU KAPISI" (5. madde olarak eklendi).
