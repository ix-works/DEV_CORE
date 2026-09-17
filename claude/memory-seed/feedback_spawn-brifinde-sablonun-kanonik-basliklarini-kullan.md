---
name: feedback_spawn-brifinde-sablonun-kanonik-basliklarini-kullan
description: "Spawn brifi lint'i İÇERİĞİ değil BAŞLIK METNİNİ arar; şablonun kanonik başlıklarını birebir kullan"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 5e1fe6d8-9f1f-4d33-863a-e185e4c67eb0
---

`watchdog_launch.py` BRIFING-LINT'i, spawn prompt'unda **iki regex** arar
(`core/scripts/hooks/watchdog_launch.py:56`, ölçüldü 2026-09-04):

```python
desenler = {"GOREV": _re.compile(r"G[OÖ0]?.?REV"), "KANIT KURAL": _re.compile(r"KANIT[ -]KURAL")}
```

⇒ Lint **içeriği denetlemez, başlık metnini arar.** Kanıt kurallarını *"KESİN KISITLAR"* ya da
*"TAHMİN YASAK"* diye eksiksiz yazsan bile, `KANIT KURAL` dizgesi geçmiyorsa uyarı ateşler.

**Why:** Uyarıyı "gereksiz formalite" sanıp yok saymak yanlış refleks — ama sebebi de yanlış
teşhis etmek (içerik eksik sanıp brifi şişirmek) vakit kaybı. Dört kez ateşledi; ilk üçünde
ek brif göndererek içerik ekledim, oysa içerik zaten vardı — **eksik olan tek şey başlıktı.**
Bu, [[feedback_ad-sayan-gate-elenen-adayi-sayar]] ile aynı sınıf: kapının NE ölçtüğünü
ölçmeden ona göre davranmak.

**How to apply:**
- Brifi yazarken `core/claude/templates/spawn-brief.md`'nin **kanonik başlıklarını birebir**
  kullan — özellikle `## 7. KANIT KURALLARI` ve `GÖREV`li bir başlık (`## 2. GÖREV SINIRLARI`).
- §7 bloğunu paraphrase etme, şablondan **aynen kopyala** (zaten "değişmez blok" diyor);
  vakaya özel karşılıklarını bloğun ALTINA ekle.
- Lint **bloklamaz, nudge'dır**. Ama tekrar ateşliyorsa kendi alışkanlığını ölç: içerik mi
  eksik, başlık mı? `grep -n "desenler" core/scripts/hooks/watchdog_launch.py` cevabı verir.
- Şablonun diğer zorunlu alanları (§6 göreve-ilişkin dersler, §8 AR-1/AR-2/AR-3 + nihai rapor
  iskeleti, ENGELLENİRSEN cümlesi) lint tarafından ölçülmez — **onları lint için değil, ajan
  işe yarasın diye yazıyorsun.** Lint sessiz diye onları atlama.

İlgili: [[feedback_ajan-kurali-brifingde-degil-taniminda-yasar]] ·
[[feedback_gate-lenmemis-kural-neredeyse-kuralsiz]] · [[feedback_standing-ajani-bos-bekletme-tek-tam-brif]]

---
**Son-dogrulama:** 2026-09-17 (core `scripts/hooks/watchdog_launch.py:57` ile dogrulandi — lint hala BASLIK dizgesi ariyor) · **Applies-to:** bu cekirdegi kullanan tum projeler

⚠ **ARAC IDDIASI** — bu ders *"bugun su arac/kapi boyle davraniyor"* der, yapisal bir olgu
degil. Arac surumu degismis olabilir: davranisa **dayanmadan once bir kez olc**. (Vaka: bir
kardes ders, dayandigi kusur duzeltildikten sonra 3 hafta bayat yasadi; tohuma alinmadan
once olculup elendi.)
