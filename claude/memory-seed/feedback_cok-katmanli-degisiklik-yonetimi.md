---
name: cok-katmanli-degisiklik-yonetimi
description: "Çapraz-kesen değişikliği katman katman keşfetme — önce tüm yüzeyi tara, sonra tek partide ilerle. ⭐ Kararın YAYILIM YÜZEYİ karar kaydına yazılır (dosya:bölüm ✅/⏳); liste tamamlanmadan karar KAPANMAZ — boş tablo kayıttan da kötüdür"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e424a095-8518-4681-bef7-a113d21aa4c0
---

Bir kusur sınıfı birden çok app/katmanı ilgilendiriyorsa (BE + FE + veri), **önce tüm yüzeyi
tara ve tek iş listesi çıkar**; bulduğunu tek tek düzeltip her seferinde yeni bir tane keşfetme.

Kanonik metodoloji: `core/playbook/howto-cok-katmanli-degisiklik.md` (2 aşama: önleme + sonradan
düzeltme, YAP/YAPMA tablosu, öz-değerlendirme listesi). Teknik kardeşi:
`core/playbook/howto-delete-guard.md`.

**Why:** 2026-07-29 silme-kontrolü turu **günlerce uzadı**. Kapsam "3 app" sanıldı; tam yüzey
taraması yapılınca gerçek tablo **7 app + 2 backend boşluğu + canlıda yetim veri** çıktı; silme
yolu 14 değil **24**'tü. Kullanıcı haklı olarak sordu: *"neden bu kadar uzadı, neden tek tek
yapıyorsun?"* Uzamanın sebebi düzeltmelerin zorluğu değil, **keşfin geç yapılmasıydı** — her
düzeltmenin review'ı aynı sınıfı yeni bir yerde buluyordu.

**How to apply:**
- Bir sınıf ikinci kez göründüğü anda **DUR** ve yüzey taraması yap (matris: hangi app · hangi
  yol · var mı yok mu · kanıt). Tarama parallel ajanlarla ucuzdur; sıralı keşif pahalıdır.
- Doğru desen bir app'te varsa, kardeşinde olmaması **BUG'dır** — "henüz yapılmamış iş" değil.
- Düzeltmeyi tek partide dağıt, sonra **taze** bug-gate koştur (ADR 0018).
- Kendi düzeltmen yeni bir yol açabilir: 2026-07-29'da 2 kez oldu (biri geri-alınabilir bir bugı
  geri-alınamaz hale getirdi). Bu yüzden gate düzeltmeden **sonra** koşar, önce değil.
- Kullanıcıya kapsamı erken ve dürüst söyle: "3 app sandım, 7 çıktı" demek, 7'yi tek tek
  keşfettirmekten iyidir.

## ⭐ EK (2026-08-19) — yüzey taraması **belgede** de geçerli: KARAR YAYILIM TABLOSU

Yukarıdaki ders **kod/app** yüzeyi içindi. Aynı mekanizma **doküman** yüzeyinde de aynen işliyor
ve orada daha sinsi, çünkü hiçbir şey patlamıyor.

**Vaka:** *"Kural A arama penceresi kaldırıldı"* kararı alındı. Karar **5 yerde** güncelleme
istiyordu; **4'ü** yapıldı. Kalan yer **normatif sözde-koddu** ⇒ belgeye sadık geliştirici
**iptal edilmiş kuralı** kodlayacaktı (hasar: mükerrer sipariş + teslimat + mal çıkışı + fatura).
Aynı gün aynı kalıp bir UI tetiğinde de tekrarlandı. Sebep analizi: o günkü **44 bulgunun ~%40'ı**
bu sınıftı — *"kaçırılmış"* değil, **düzeltme turunun kendi ürettiği** bulgular.

**Kök sorun:** kararın **kaç yere dokunması gerektiği hiçbir yerde yazmıyor** ⇒ tamamlandığı
**ölçülemiyor**. *"4 yeri güncelledim"* ile *"bitti"* arasındaki farkı kimse göremiyor.

**Çare — karar kaydı yayılım tablosu taşısın:**
```
**Yayılım** (karar bu yerlerin HEPSİ güncellenmeden KAPANMAZ):
| Hedef                          | Durum |
|--------------------------------|-------|
| ts-parts/TS-04-MOTOR.md §4.5.6 | ✅    |
| ts-parts/TS-03-DDIC.md §3.10   | ⏳    |
```
⛔ **Boş ya da eksik yayılım tablosu ⇒ kayıt geçersiz.** Tablo koyup boş bırakmak, tablo
koymamaktan **daha kötüdür** — koruma sanısı üretir (fail-open).
⭐ **Yayılım yüzeyi belgelerle bitmez — ÜRETİLMİŞ artefaktın KAYNAĞINI da kapsar.**
2026-08-19'da bir metin düzeltmesi tüm belgelerde yapıldı, ama **iki üreteç script'inde** ve bir
**üretilmiş HTML/PNG'de** kaldı ⇒ bir sonraki üretimde **geri gelecekti** (düzeltme kalıcı değil,
sadece görünmez olmuştu). Düzeltmeden önce sor: *"bu dosya üretilmiş mi, kaynağı nerede?"*
(o projede: TS → `ts-parts/` · EK-A → `ek-a-rap-src/` · mockup → `mockup-src/`).

⚠ **Geriye dönük doldurma yapma** — pahalı, değeri düşük. Kuralın başladığı tarihi yaz, eskilere
tek satır not düş.

İlgili: [[once-yuzey-taramasi-sonra-is-listesi]] · [[done-tam-kapsam-dogrula]] · [[kararlari-once-topla-sonra-dispatch]] · [[feedback_duzeltme-turu-kendi-ciktisina-kapi-ister]]
