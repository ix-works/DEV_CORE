---
name: feedback_is-parametresini-koda-gomme-onerme
description: "Kullanılan bir iş parametresini (eşik, mesafe, yüzde) koda sabit gömmeyi ÖNERME — kullanılacaksa ayar tablosunda kalır; gereksizse tümden kaldırılır"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: b1b58519-2c91-4830-aeab-6f0c875a0510
---

Kullanılan iş parametresi koda sabit olarak gömülmez. Kullanılıyorsa ayar tablosunda kalır; gereksizse alan ve mantık birlikte kaldırılır.

Kullanıcının sözü (bir rapor paketinin ayar tablosu sadeleştirmesi, 30.10.2026): *"koda gömme, kullanılacaksa tabloda kalsın"*. Önerilen "karşılaştırma kartının 3 ayarı (%8, %25, 8 hafta) kodda sabit olsun" seçeneğine verdiği cevaptı. Aynı turda gerçekten hatalı olan alanı (adet bazlı asgari miktar) kaldırmayı ise onayladı.

**Why:** İş değerini koda gömmek, her ayar değişikliğini geliştirme işine çevirir. FS'teki "iş değerleri kodda sabit değil" kuralı kullanıcının bilinçli tercihidir. "Az kullanılıyor" gerekçesi bu kuralı gevşetmez.

**How to apply:** Bir ayar tablosunu sadeleştirmeyi değerlendirirken önce şunu sor: alan gerçekten kullanılıyor mu?
- Kullanılmıyorsa ya da tasarımı hatalıysa: kaldır.
- Kullanılıyorsa: tabloda kalır. "Koda sabit" seçeneğini önerme.

Son-doğrulama: 2026-10-30 · Applies-to: tüm projeler, Z ayar tabloları / FS iş parametreleri
prior-art: yok ([[feedback_sorulari-tek-tek-sor-oneriyle]] ile aynı turda)
