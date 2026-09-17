---
name: feedback_once-sonra-kanitinin-zaman-damgasini-kontrol-et
description: "Ajanın sunduğu 'önce/sonra' kıyasında iki çıktı dosyasının zaman damgası AYNIYSA, kıyas trivially-true olabilir — 'ESKİ' dosya aslında yeni kodla üretilmiş olabilir. Kıyasın kendisi de bir iddiadır."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7be4eb27-4593-4b9b-a0fd-793cd5aa7970
---

**KURAL:** Bir ajan *"düzeltmeden önce şöyleydi, sonra böyle oldu"* diye **iki çıktı dosyası**
sunduğunda, dosyaların **zaman damgasına ve boyutuna bak**. İkisi de aynıysa şüphelen: "ESKİ"
etiketli dosya, düzeltmeden önce değil, **aynı koşumda yeni kodla** üretilmiş olabilir. O zaman
`diff` boş çıkar ve bu **hiçbir şey kanıtlamaz** — regresyon yokluğu değil, kıyasın yokluğudur.

**Ölçülmüş vaka (2026-09-09, ZSD001 toplama listesi FE B-turu).** Ajan *"ilk turun 13
senaryosunun çıktısı byte-byte aynı"* dedi ve kanıt olarak `harness_out_TUR1.txt` ↔
`harness_out.txt` gösterdi. `ls -la`: **ikisi de 6534 bayt, ikisi de 09:00**. Yani "TUR1"
dosyası B-turundan sonra üretilmiş olabilirdi ve `diff -q`'nun boş dönmesi tautoloji olurdu.
Doğrulama yolu: ajanın kendi negatif-kontrol kopyasını (`PickPrint.blegacy.js` — yalnız ilgili
düzeltmeleri geri alınmış) **kendim koştum**. Sonuç gerçekten ayrıştı: `3 ST istendi / 2,6 var`
→ ESKİ `"3 · 3 · 0 eksik"` ↔ YENİ `"3 · 2,6 · 0,4 eksik"`, ve kaba vakalar (`10/4`, `3/0`)
iki tarafta **birebir aynı** kaldı. Yani iddia DOĞRUYDU — ama sunulan kanıt onu kurmuyordu.

**Why:** *"Ölçüm doğru, yorumu yanlış"* sınıfının kardeşi bu: burada **ölçüm aracı** (`diff`)
doğru çalışıyor, **girdisi** yanlış. Ve bu sessiz bir kusurdur — `diff -q` rc=0 verir, ekranda
yeşil görünür, hiçbir uyarı çıkmaz. Ajanın kötü niyeti gerekmez: harness'ı iki kopyayı da tek
koşumda üretiyorsa "TUR1" adı bir **etiket**tir, tarihsel bir artefakt değil.
[[feedback_exit0-degil-cikti-kaniti]] "exit 0 ≠ kanıt" derken bunu da kapsar: burada
`diff` boşluğu da bir "exit 0"dır.

**How to apply:**
- İki-dosya kıyası gördüğünde **önce `ls -la`**: farklı mtime + makul bir sıra bekle. Aynı
  mtime = kıyas kurulmamış olabilir.
- Asıl çözüm **kıyası yeniden kurmaktır**, dosyaya bakmak değil: negatif-kontrol kopyasını
  (düzeltme geri alınmış sürüm) **kendin koştur**. Ajanlar bunu genelde üretiyor — sen sadece
  çalıştır. ([[feedback_yesil-regresyon-suiti-duzeltmenin-kaniti-degildir]] aynı ailedendir:
  süit ters yönde de yeşilse kördür.)
- Ayırt edici test şudur: **kaba vaka değişmemeli, ince vaka değişmeli.** İkisi birden
  değişiyorsa düzeltme fazla geniş; ikisi birden aynıysa kıyas kurulmamış.
- Kıyasın kendisi bir iddiadır — [[feedback_curutme-de-bir-iddiadir-yerine-yazilan-sayi-olculur]]
  ve [[feedback_kanit-yeniden-uretilebilir-bicimde-yazilir]] ile aynı disiplin: kanıtı
  **yeniden üretilebilir** biçimde iste, üretilmiş hâline değil.
- Brife önden yaz: *"negatif kontrolü ayrı dosya olarak bırak, ben kendim koşacağım."*
