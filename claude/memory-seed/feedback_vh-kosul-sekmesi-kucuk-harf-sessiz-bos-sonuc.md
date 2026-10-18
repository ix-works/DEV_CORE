---
name: feedback_vh-kosul-sekmesi-kucuk-harf-sessiz-bos-sonuc
description: "ValueHelpDialog 'Koşulları tanımla' sekmesine küçük harfle yazılan değer olduğu gibi BE'ye gider; DDIC LOWERCASE boş anahtarda (VKORG/KUNNR/MATNR/FKART) eşleşmez → HATASIZ boş sonuç. Çeviri FE'de, range değer1/değer2'de"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: 8865df6b-2e94-44e8-8952-84b42fc53742
  modified: 2026-10-15T21:21:14.573Z
---

ValueHelpDialog'un **"Koşulları tanımla"** sekmesine yazılan değer (ör. `EQ zx01`, `Contains s07`; değerler temsilî) token'a
**olduğu gibi** girer; seçim kurucu range'i bu hâliyle BE'ye yollar. Alanın domain'inde `LOWERCASE` boşsa
veritabanında küçük harfli anahtar yoktur ⇒ sorgu **hatasız 0 satır** döner. Kullanıcı "veri yok" sanar.

**Vaka (bir projede, 2026-10-15, FE bug-gate tur 6):** koşul `EQ zx01` → istek `EQ zx01`, Özet 0 satır;
büyük harfli kontrol `EQ ZX01` → 2 satır. İkinci yüz: yazılı `ZX01` ile VH koşulu `zx01` harf-duyarsız
"tekrar" sayılıp yazılı olan silindi, BE'ye yalnız küçük harf gitti. Düzeltme: seçim kurucuda range
`value1`/`value2` `.toUpperCase()` (tek nokta, tüm alanlar). Kontrol: DD01L.LOWERCASE 4 alanda boş; MARA/KNA1/
TVKO/TVFK'de küçük harfli anahtar 0 (901 satır). tr-TR'de `'zi'.toUpperCase()` = `ZI`, `'ı'` → `I`.

**Why:** Ayrıştırıcı BE (JSON range → SELECT) harf çevirmez; Enter ile yazılan metni büyüten doğrulayıcı
VH koşul sekmesini görmez — iki giriş yolu ayrı kod yoludur.

**How to apply:** VH'li her filtrede seçim kurucuda range değerlerini büyük harfe çevir (alanın domain'i
`LOWERCASE` boşsa). Test: koşul sekmesine küçük harf + aynı değerin büyük harfli kontrolü yan yana.
`ß`→`SS` gibi uzayan çevrim BE uzunluk denetimine düşer (görünür hata, sessiz değil).

Son-doğrulama: 2026-10-15
Applies-to: freestyle UI5 + sap.ui.comp ValueHelpDialog + JSON/range seçim taşıyan V2 function import
prior-art: yok (memory grep "LOWERCASE|toUpperCase|küçük harf" 2026-10-16; `feedback_gateway-substringof-maxlength-400-ve-tr-harf-sinifi` Gateway $filter harf sınıfıdır, bu yol değil). Kardeş ilişki: [[feedback_vhd-exclude-bos-dizi-gizlemez-sessiz-dusme]]
