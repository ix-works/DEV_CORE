---
name: feedback_literal-filtreli-ab-runtime-hatasini-yeniden-uretemez-pushdown
description: "Literal filtreli SQL A/B'si, filtre değeri çalışma zamanında belirlenen bir runtime hatasını yeniden üretemez — HANA literal'i view'a iter (pushdown), zehirli satıra hiç değmez"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 84facfd3-9151-4893-8380-15c2cfd0d393
---

Bir runtime hatasını elle SQL ile "yeniden üretmeye" çalışırken **filtre değerini literal yazmak
ölçümü kör eder.** HANA, PREPARE anında sabit olan bir filtreyi view'ın **içine iter** (pushdown)
ve bozuk satırları hiç değerlendirmez. Değer çalışma zamanında belirleniyorsa (iç tablo, alt-sorgu,
`INNER JOIN @itab`) itemez, **tüm view** değerlendirilir ve hata çıkar.

**Aynı sonuç kümesi, farklı sonuç** — 2026-09-08, ZSD001 booking `SQL 305` (ölçüldü):

| Sorgu | Mantıksal sonuç kümesi | Sonuç |
|---|---|---|
| `WHERE BookingNo = '7700000035'` (literal) | 1 satır | ✅ OK |
| `WHERE BookingNo = ( SELECT MAX(booking_no) FROM zsd001_t_bookhd )` (MAX = aynı değer) | **aynı 1 satır** | ⛔ **305** |

RAP'in `READ ENTITIES ... BY \_assoc` okuması **ikinci sınıftır**: framework
`<view> AS PERS INNER JOIN @IT_WITH_PRIMARY_KEY AS KEYTAB ON ...` kurar; iç tablonun içeriği
PREPARE anında görünmez ⇒ pushdown olmaz.

**Why:** Ben `BookingNo='7700000034'` literal'iyle A/B yapıp **200 / 1 satır** aldım ve
*"34 sağlam, sorun yalnız 32'de"* diye hüküm kurdum. Üretimde `7700000034` **üç kez dump etti**
(10:05:57 · 10:06:07 · 10:07:06). Ölçüm doğruydu, **çıkarım yanlıştı** — ve bu, kök nedeni
"tek zehirli satır" sanmaya, halkayı "açık" bırakmaya yol açtı
([[feedback_ajan-bulgusu-dogru-mekanizmasi-yanlis]]).

**How to apply:** Bir runtime hatasını SQL ile yeniden üretirken (a) filtreyi **runtime'a benzet** —
literal yerine alt-sorgu / iç tablo JOIN'i kullan, ya da **filtresiz** koş; (b) literal filtreyle
alınan ✅ sonucu **"o kayıt sağlam"** diye yazma — yalnız *"literal filtreyle pushdown oluyor"*
demektir; (c) bozuk satırı **kapsayan** ve **dışlayan** iki sorguyu birlikte koş — fark
mekanizmanın kendisidir. İlgili: [[feedback_cds-tekillik-olcumunde-alan-listesi-bulguyu-degistirir]]
(aynı vakada alan listesi de bulguyu değiştiriyordu) · [[feedback_yesil-regresyon-suiti-duzeltmenin-kaniti-degildir]].
