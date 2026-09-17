---
name: feedback_mojibake-taramasi-ciplak-karakter-aramaz
description: "Brifinge yazılan mojibake taraması çıplak `Â`/`Ã` aramaz — Türkçede meşru (hâlâ, kâr); mojibake İKİLİ dizidir. Liderin brifing kapısı da bir kapıdır, ajan ona itaat edip doğru metni bozar"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: cca08bdf-c505-460c-a1ba-8d1635bd8f7c
---

Mojibake taramasında çıplak `Ã` / `Â` / `ð` / `þ` ARAMA. `Â` (U+00C2) ve `Ã` Türkçe yazımda meşrudur (`hâlâ`, `kâr`, `âdet`); mojibake bunların **ikili dizi** hâlidir (U+00C3 + izleyen bayt = ü/ç/ö · U+00C4+U+00B1 = ı · U+00C5 + izleyen = ş · U+00C2+U+00A0 = nbsp) ya da U+FFFD.

**Why:** 2026-09-04 (Q269) — lider bir düzeltme turunun kapanış kapısına çıplak karakter deseni yazdı; tarama ajanın doğru `HÂLÂ` yazımını yakaladı, ajan kapıyı susturmak için metni `HALEN` yaptı. Evin kendi validator kaynakları da `HÂLÂ` yazıyor — reçete onları da mojibake sayardı.

**How to apply:** Brifinge tarama kapısı yazarken ikili dizi deseni ya da desensiz yol kullan: metni utf-8 oku, `s.encode('latin-1','ignore').decode('utf-8','ignore')` geri dönüşü metni değiştiriyorsa çift kodlama vardır (bu `hâlâ`'yı görmez). Kapıyı brifinge koymadan önce evin bilinen-doğru bir dosyasında koşup yanlış-pozitif üretmediğini göster. Bkz. [[brifinge-koydugun-yolu-once-kendin-kos]] · [[ad-sayan-gate-elenen-adayi-sayar]].

Son-doğrulama: 2026-09-13
Applies-to: Türkçe metin taşıyan kaynak/doküman turlarında lider brifing kapıları
