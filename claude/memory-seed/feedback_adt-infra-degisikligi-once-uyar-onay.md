---
name: adt-infra-degisikligi-once-uyar-onay
description: "ADT-ilişkili script/kural/MCP/hook/validator değişikliğinden ÖNCE highlight'lı uyar + bilgilendir + önem-kategorili AÇIK onay iste"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9548d6ed-a1eb-45a3-a12a-b9873f4b16c7
---

ADT ile ilişkili altyapıda (scripts/, kurallar, MCP server, hook'lar, validator) değişiklik yapmadan ÖNCE: kullanıcıyı **HIGHLIGHT** biçimde uyar → ne yapacağını + neden + blast-radius bilgilendir → **önem kategorisine göre (HIGH/orta) açık onay iste**. Bir iş listesinin arasına gömülü tek-satır onay = YETERSİZ; ADT-infra maddesi ayrıca öne çıkarılıp tek-tek onaylanır.

**Why:** ADT altyapısı paylaşılan + SAP-yazma yolunu etkiler; sessiz/gömülü değişiklik kullanıcının kontrolünü kaybettirir. Somut olay (2026-06-21): v1 drift-fix'i iş listesi arasında highlight'sız/onaysız uygulandı, sonra (kanıt incelemesiyle yanlış kapsamda olduğu görülüp) geri alınması gerekti.

**How to apply:** SAP-yazma yolu / MCP server / hook / validator / drift-pull mantığı dokunuşu = **HIGH** → highlight + tek-tek onay, kararı bekle. Salt-okunur analiz, repo-içi app kaynağı (FE/BE build), doküman bu kapsamda DEĞİL. Önem kategorisini her seferinde belirt. İlgili: [[feedback_arac-kod-fix-lider-isi]] [[feedback_kural-gate-lenmeli-yoksa-anlamsiz]] [[feedback_karar-verimliligi-asiri-kapi-yok]] [[feedback_soru-once-tartis-act-etme]]
