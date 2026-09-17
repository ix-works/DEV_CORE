---
name: feedback_calisan-ajanin-dosyasi-ucus-halindedir-iddia-degil-soru
description: "Çalışan bir ajanın dosyasında gördüğün eksik, İDDİA değil SORU olarak gönderilir — editör diagnostiği/grep anlık bir kesittir ve ajan gövdeyi yazıp import'u sonra ekler. Uçuş hâlindeki dosya durumu sonuç değildir."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 78c7bae5-81aa-4c75-a44f-1fc2d4679222
---

**KURAL:** Bir alt ajan **koşarken** onun dosyasını ölçtüysen, bulduğun eksiği **iddia olarak
gönderme** — soru olarak gönder: *"X eksik görünüyor; hâlâ yazıyorsan yok say, bitirdiysen bu bir
regresyon."* Ölçümün, ajanın iki `Edit`'i arasına denk gelmiş olabilir.

**Ölçülmüş vaka (2026-09-09, ZSD001 gece turu).** `atom.py`'de `time.time()` çağrısı gördüm,
import bloğunda `import time` yoktu ⇒ *"düzeltmen bir regresyon üretti, `NameError` verir"* diye
yazdım. Ajan çürüttü: `import time` **ekliydi**; tarama, gövdeyi yazdığı ile import'u eklediği
edit'in **arasına** denk gelmişti. Ajan kanıtını `py_compile` ile değil **7 yardımcıyı fiilen
çağırarak** üretti ve ayrıca `dis` ile 43 fonksiyonun `LOAD_GLOBAL`'larını çözüp *"çözülmeyen ad: 0"*
gösterdi.

⛔ **Aynı sınıf o oturumda ÜÇ KEZ tekrarladı** — üçüncüsü, "bir daha yapmayacağım" diye yazdığım
mesajdan hemen sonra. Yani bu bir dikkat sorunu değil, **yapısal**: ajanlar dosya yazarken ara
durumlar üretir, ve editör diagnostiği/`grep` sana o ara durumu **hatasız biçimde** raporlar.
Ölçüm doğrudur; **yorumu** yanlıştır.

**Why:** Yanlış bir regresyon suçlaması üç şeye mal olur: (a) ajan işini bırakıp savunma kanıtı
üretir — zaman kaybı (b) liderin ölçümüne olan güven aşınır; sonraki gerçek bulgu da tartışılır
(c) *"kanıtlı hareket et"* disiplini, kanıtın **zamanlamasını** ihmal ederek ihlal edilmiş olur.
`py_compile`/`node --check` de bu sınıfı örtmez: tanımsız isim **çalışma zamanı** hatasıdır,
`rc=0` hiçbir şey söylemez — yani "temiz derledi" ile "ara durumdaydı" aynı görünür.

**How to apply:**
- Ajan **koşuyorsa**: bulguyu her iki ihtimali kapsayacak şekilde yaz. *"Hâlâ yazıyorsan yok say"*
  cümlesi bir nezaket değil, **ölçümün kapsam niteleyicisidir**.
- Ajan **"KOD DONDU" / bitti dediyse**: o zaman iddia kurabilirsin — ama önce dosyayı **yeniden
  oku**, elindeki eski kesitle konuşma.
- Kesin konuşman gerekiyorsa **dosyayı dondur**: md5 al → 30 sn bekle → tekrar al. Değişiyorsa
  hâlâ uçuşta. ([[feedback_kapi-kosarken-dosya-donar-md5-teyidi]] aynı mekanizmanın kardeşi.)
- Tanımsız-isim sınıfını doğrularken **çağrı düzeyine in**: fonksiyonu gerçekten koştur, ya da
  `dis` ile `LOAD_GLOBAL`'ları isim uzayına karşı çöz. Göz taraması bu iş için yetersizdir
  ([[feedback_kopya-sayimi-tek-sozdizimi-desenine-dayanma]]).
- Yanıldığında **düzelt ve yöntemi değiştir**, yalnız özür dileme: burada değişen şey
  *"ajan koşarken bulgu = soru"* kuralıdır.

İlgili: [[feedback_ajan-bulgusu-dogru-mekanizmasi-yanlis]] ·
[[feedback_curutme-de-bir-iddiadir-yerine-yazilan-sayi-olculur]] ·
[[feedback_exit0-degil-cikti-kaniti]] · [[feedback_kapsam-niteleyicisini-dusurme]] ·
[[feedback_duzeltme-turu-kendi-regresyonunu-uretir]]
