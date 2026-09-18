---
name: feedback_kapsam-niteleyicisini-dusurme
description: "Bir ölçümü aktarırken kapsam niteleyicisini düşürmek doğru cümleyi YANLIŞ yapar — \"HLEVEL=02'de boş\" ≠ \"28 satırın tamamında boş\"; sayı iddiası açılıp sayılmadan aktarılmaz"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 135c882f-c5bd-4a31-994f-f5aa4f3fd199
---

**KURAL:** Bir ölçüm sonucunu **aktarırken** (rapordan belgeye, kapıdan düzeltmeye, ajandan lidere)
**kapsam niteleyicisi cümlenin içinde kalır.** Niteleyiciyi düşürmek, doğru bir ölçümü **yanlış bir
iddiaya** çevirir — ve aktarılan hâli artefaktta kaldığı için orijinal ölçümden daha uzun yaşar.

**En pahalı vaka (2026-08-22, <PAKET-F> `RESEARCH-09`):** Kapı ölçtü → *"**HLEVEL=02** segmentlerin
tamamında `PARSEG` boş"* (**doğru**). Düzeltme turu bunu → *"**28 satırın** tamamında boş"* diye
aktardı ve tablonun 28 satırının hepsini `*(boş)*` yaptı. Canlı ölçüm: **13 satırda PARSEG DOLU**
(HLEVEL 03/04 → `E1EDP01`/`E1EDKT1`/`E1EDPT1`). ⇒ Önceki sürümün o 13 satır için verdiği bilgi
**doğruydu**; "düzeltme" **doğrulanmış veriyi doğrulanmamış çıkarıma geri düşürdü**.
⛔ Üstelik kontrol grubu **tersine kullanıldı**: *"DELFOR02'de dolu, INVOIC02'de kanıt yok"* denmiş;
gerçek sayılar DELFOR02 **9**, INVOIC02 **13** — geçen kontrol, yanlış negatifi **pekiştirmişti**.

**Aynı sınıf, AYNI GÜN beş kez:**

| # | Aktarılan | Gerçek |
|---|---|---|
| 1 | segment sayısı *"11"* (başlık) / *"13"* (kaynaklar) / *"7"* (gövde) | tek kaynağa bağlanmamış |
| 2 | ATC borcu *"5 bulgu"* | *"5 nokta / 9 verdict"* — **birim** farkı |
| 3 | yorum-dışı satır *"127"* ↔ *"116"* | filtre tanımı farkı (11 başlık satırı) |
| 4 | gümrük alanı *"7 alan"* | `ZOLLA+ZOLLB+ZOLL1..6` = **8** |
| 5 | `PARSEG` *"28 satırın tamamı"* | **13'ü dolu** |

**NASIL UYGULA:**
1. **Niteleyiciyi taşı.** Ölçüm *"X koşulunda"* diyorsa aktarımın da öyle desin. Genelleme
   yapacaksan **yeni bir ölçüm** gerekir, cümle kısaltması değil.
2. ⭐ **Sayı iddiasını AÇIP SAY.** Gruplu/aralıklı yazım (`ZOLL1-6`, `BANR01-10`) meşrudur ama
   *"N/N tam"* bir **aritmetik iddiadır** — grupları açıp toplamı doğrulamadan aktarma.
3. **Birimi yaz.** *"5"* yetmez: *nokta* mı, *verdict* mi, *dosya* mı, *satır* mı?
4. **Bir sayı iki yerde yaşıyorsa** biri bayatlar (`DOC-CR-02`). Tek kaynağa bağla, ötekine link ver.
5. **Kontrol grubunu yönüyle oku:** kontrolün *geçmesi*, öznenin ölçümünü doğrulamaz — özne ayrıca
   ölçülür. Yoksa geçen kontrol yanlış negatifi **pekiştirir**.

[[feedback_kontrolun-kapsami-is-akisinin-seklinE-bagli]] · [[feedback_yesil-sinyalin-kapsamini-sor]] ·
[[feedback_tarama-ciktisi-hipotezdir-is-listesi-degil]] · [[feedback_iddia-yazma-aninda-kanit-kurallari]]

---

**Vaka (2026-08-27) — "YANLIŞ SAYI" bulgusunun İLK sorusu: *hangi evren?***

Bir inceleme, <MUSTERI-A> şartnamesindeki iki sayıyı *"yanlış"* diye işaretledi
(`820.402` ve `10.094`). Ölçüldü:

| Evren | DTM `102` | `LIN` `D_1229` boş |
|---|---|---|
| tüm klasör (746 dosya, DELFOR + **ORDERS**) | **820.402** | **10.094** |
| yalnız DELFOR (726 dosya / 10.071 mesaj) | **820.360** | **10.071** |

⇒ Sayılar **yanlış değildi** — **kapsam niteleyicisi eksikti.** Fark tam olarak **19 `ORDERS`
mesajı** (42 DTM + **23** `LIN` segmenti — ⚠ mesaj ≠ segment: 19 mesaj 23 `LIN` taşıyor).
Mapping yalnız DELFOR'a baktığı için **alan iddiaları** DELFOR evrenini ister; ama üreticinin
*"746 dosyanın tamamı tarandı"* bloğunda `820.402` **doğru sayıdır**.

**Düzeltme biçimi:** şartnamede sayı DELFOR evrenine çekildi **ve her iki evren yazıldı**;
üreticide sayı **DEĞİŞTİRİLMEDİ**, yalnız niteleyici eklendi. Körü körüne "düzeltmek" doğru
sayıyı bozacaktı.

📌 **Kural:** *"bu sayı yanlış"* bulgusunu almadan önce **iki tarafın evrenini** sor. İki doğru
sayı, iki farklı evrende **çelişki gibi görünür**.
