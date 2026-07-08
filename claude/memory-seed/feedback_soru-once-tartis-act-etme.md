---
name: feedback_soru-once-tartis-act-etme
description: "Kullanıcı SORU sorduğunda hemen edit/commit/kural-ekleme yapma — önce cevapla+tartış, onay gelince uygula"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: cbd3c1b7-21b6-433c-9916-4307c1ea6587
---

Kullanıcı (2026-06-19) bug-gate'in pure-FE işte BE-checklist'e bakıp **zaman kaybedip kaybetmediğini SORDU** (anlamak/tartışmak için). Ben hemen bug-expert tanımını edit'leyip commit'ledim. Kullanıcı: **"ben soru sordum sen hemen ekleme yaptın."** Üstelik encode ettiğim gerekçe ("orada değişen yok → kontrol edilecek de yok") **kendisi de hatalıydı** — BE tarafının temiz olduğunu varsayıyordu; oysa bir alan/CDS daha önce (hatta başka session'da) başka iş için değişmiş + düzgün kontrol edilmemiş olabilir (latent kusur). Edit geri alındı (revert).

**Why:** Soru = düşünme/tartışma daveti, uygulama emri DEĞİL. Hemen act etmek (a) kullanıcıyı rahatsız eder (kontrolü elinden alır), (b) yarı-düşünülmüş/yanlış kuralı kalıcılaştırma riski taşır. "Encode-it kültürü" var diye HER içgörüyü anında commit'lemek yanlış — önce doğruluğunu ve kullanıcı mutabakatını al.

**How to apply:**
- Kullanıcı SORU sorduğunda (özellikle "X sorun olabilir mi?", "şöyle mi yapıyorsun?", "neden böyle?") → **CEVAPLA + trade-off'ları tartış + (varsa) öneri+gerekçe sun → DUR.** Edit/commit/kural-ekleme YAPMA; "uygulayayım mı?" diye onay iste.
- Yalnız kullanıcı net "yap/ekle/düzelt" dediğinde uygula. Net değilse soru-modundadır.
- Bu, [[feedback_karar-verimliligi-asiri-kapi-yok]]'nın İKİZİ: o "gereksiz çok SORMA (makul default varken ilerle)"; bu "soruya gereksiz çok ACT etme (tartışma beklerken commit'leme)". İki uç da yanlış — ayrım: kullanıcı İŞ mi verdi (ilerle) yoksa SORU mu sordu (tartış)?
- İlgili: [[feedback_kararlari-once-topla-sonra-dispatch]], [[feedback_done-tam-kapsam-dogrula]].
