---
name: feedback_yesil-regresyon-suiti-duzeltmenin-kaniti-degildir
description: Yeşil bir regresyon süiti düzeltmenin ÇALIŞTIĞINI kanıtlamaz — süiti düzeltme ÖNCESİ sürümde de koş; o da yeşilse ağ KÖRDÜR. Her düzeltme turu ayırt edici test + aşırı-baskılama KONTROL testi ister
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c20182a3-2866-4571-9b91-5c1f1e595fd2
---

**Süit yeşili iki farklı şey söyleyebilir ve ikisi karıştırılır:** *"regresyon yok"* (eski davranış
korundu) ile *"düzeltme çalışıyor"* (yeni davranış gerçekten değişti). Bir süit **yalnız birincisini**
söylüyor olabilir ve bunu **kendisi haber vermez**.

**Ayırt eden tek ölçüm — TERS YÖN KOŞUSU:** aynı süiti düzeltme **ÖNCESİ** sürümde de koş.
- fix öncesi **KIRMIZI** → süit ayırt edicidir, yeşil bir kanıttır.
- fix öncesi de **YEŞİL** → **süit KÖRDÜR**; o turun kanıtı **yoktur** (yalnız regresyon yokluğu vardır).

**Vaka (2026-09-05, ZSD001 EKR-04 `InvAlloc`).** Kapı *"süit yeşili bu turun kanıtı değil"* dedi;
ölçüldü ve haklı çıktı: **42 testlik süit HEM düzeltilmiş HEM `55e1b827` (fix öncesi) sürümde
42/42 PASS** verdi. F1'i yakalayan ağ, tam da F2'nin açtığı iki yeni sahayı **görmüyordu**.
Yedi test eklendi (R4-1..R4-7) ⇒ **49/49** (yeni) ↔ **44/49** (fix öncesi): beş test ayırt edici.

**Why:** Testler bulunan **vakaya** göre yazılır, düzeltmenin dokunduğu **sınıfa** göre değil.
Düzeltme sınıfı genişletince (burada: aynı yanlış üç sahadan **dörde** taşındı) ağ yerinde kalır ve
büyümüş yüzeyin dışını görmez. Yeşil o an en tehlikeli sinyaldir — **aramayı durdurur**.

**How to apply — her düzeltme turunda:**
1. Süiti **iki yönde** koş (yeni sürüm + `git show <önceki>:<dosya>` ile çıkarılmış eski sürüm).
   Sonucu **iki sayı olarak** yaz: `49/49 ↔ 44/49`. Tek sayı verilen rapor eksiktir.
2. En az bir **AYIRT EDİCİ** test: fix öncesinde **düşmek zorunda**.
3. En az bir **KONTROL** testi: düzeltmenin **aşırıya kaçmadığını** ölçer (burada: homojen grupta
   dört saha **hâlâ** etiketli · komşu lot etkilenmiyor). Aksi hâlde "hepsini bastır" da testi geçer.
4. Testin **kendi kusurunu** kodun kusuru sanma: sahte-FAIL'lerin ikisi de testtendi — i18n stub'ı
   anahtar adını döndürüyordu (ham metinde harf aramak DAİMA true) ve grid durumu yalnız
   `r.Touched` iken kuruluyordu. Bir FAIL'i "kod hatası" ilan etmeden önce **stub'ı ve ön koşulu** oku.
5. Raporun sonunda **"süit hâlâ neyi göremiyor?"** sorusunu açıkça cevapla.

⚠ Süit **repoda değilse** bu disiplin her turda sıfırdan yeniden türetilir — ağın kendisi de
bir teslimattır; scratchpad'de bırakmak **yapısal boşluktur**.

İlgili: [[feedback_yesil-sinyalin-kapsamini-sor]] · [[feedback_ters-yon-kontrolu]] ·
[[feedback_duzeltme-turu-kendi-regresyonunu-uretir]] · [[feedback_duzeltme-turu-kendi-ciktisina-kapi-ister]] ·
[[feedback_exit0-degil-cikti-kaniti]] · [[feedback_kapi-zinciri-derlemeyi-gormez]]
