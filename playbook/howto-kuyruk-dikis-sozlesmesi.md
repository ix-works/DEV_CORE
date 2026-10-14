---
applies_to: [ecc, s4_private, s4_public, btp_abap]
layer: L3
scope: project-wide
type: playbook
applies-to: tooling
last-updated: 2026-10-12
status: active
---

# HOWTO — "Kuyruk-dikiş" sözleşmesi: toplu yapay zekâ yargısını kodla dikmek

> **Ne:** çok sayıda kalem için *hesaplanamayan* bir yargının (ör. bir ATC bulgusu nasıl düzeltilmeli,
> bir eşleme satırı hangi hedef alana gider, bir kalemin etkisi ne) modelden alınıp deterministik bir
> araç zincirine **güvenli** bağlanması için yazılı desen.
> **Ne değil:** gate, araç ya da yeni bir kayıt yeri değildir (ADR 0019). Bir toplu iş tasarlanırken
> bu sayfadaki beş madde **tasarım kontrol listesi** olarak kullanılır.
> Fikir kaynağı: dış bir pazardaki toplu analiz hattında görülen "yargı kuyruğu" yapısı — bizim kanıt
> kurallarımızla (bulunamadı ≠ yok · model beyanı kanıt değildir) uyumlu olduğu için **desen** olarak
> alındı; o hattın kodu, şemaları ve güven eşikleri **alınmadı**.

## 1. Sözleşme — beş madde

| # | Madde | Neden |
|---|---|---|
| **KDS-1** | **Yargı dosyada yaşar.** Araç önce cevaplanacak kalemleri bir kuyruk dosyasına (JSON/CSV) yazar; model cevabını **o dosyaya** yazar; araç ikinci adımda dosyayı okur. Sohbet metni girdi değildir. | Cevap denetlenebilir, tekrar üretilebilir ve git diff'iyle gözden geçirilebilir olur. |
| **KDS-2** | **Doğrulama kodda yapılır.** Her cevap alanı izin verilen değer kümesine / tipe / kimliğe karşı **kodla** denetlenir (kuyrukta olmayan kimlik, bilinmeyen karar değeri, boş zorunlu alan). Modelin "kontrol ettim" demesi doğrulama değildir. | Model beyanı kanıt değildir; deterministik kontrol sessiz kaymayı yakalar. |
| **KDS-3** | **Bozuk girdi DURDURUR ve adlandırır.** Doğrulanamayan kalemde araç sessizce atlamaz, varsayılan değer uydurmaz; **hangi kalem, hangi alan, neden** bilgisini basıp sıfırdan farklı çıkış koduyla durur. | Kısmi işlenmiş toplu iş, hiç işlenmemişten daha tehlikelidir (hangi kalemin işlendiği belirsizleşir). |
| **KDS-4** | **Cevapsız alan BOŞ kalır.** Model bir kalem için yargı veremiyorsa alan boş bırakılır; araç bunu "açık" olarak sayar ve çıktısında **ayrı sayı** olarak basar. Tahmini doldurma yasaktır. | Bulunamadı ≠ yok: boş, "karar verilmedi" demektir; doldurulmuş tahmin, kararla ayırt edilemez. |
| **KDS-5** | **Yeniden koşum verilmiş cevapları korur.** Kuyruk yeniden üretildiğinde (yeni kalem eklendi, kaynak değişti) mevcut cevaplar kimlikle eşlenip taşınır; yalnız yeni/değişen kalem boş gelir. Kimliği değişen kalemin eski cevabı **taşınmaz**, raporlanır. | Tekrarlı turda emek kaybolmaz, ama bayat cevap da yeni kaleme yapışmaz. |

**Kalem kimliği** kaynakta kararlı olmalıdır: satır numarası, dizi sırası ya da zaman damgası kimlik
olamaz (bir kaydırma her kalemi "yeni" yapar). ATC için örnek kimlik: obje + birim + `checkId` + mesaj
— [`howto-atc-duzeltme-kaliplari.md`](howto-atc-duzeltme-kaliplari.md) §0.

## 2. Kapsam beyanı (çıktı her koşumda basar)

Araç her koşumda en az şunları yazar — sıfır-sonuç anı en kritik andır (CLAUDE.core §7 KAPSAM BEYANI):
`toplam kalem · cevaplı · boş (açık) · reddedilen (KDS-3) · taşınan eski cevap (KDS-5) · düşen eski cevap`.

## 3. Bizim katmanlarla ilişki

- **Açık madde tek yerde yaşar** (CLAUDE.core §1.1 KAPANIŞ DİSİPLİNİ): kuyruk dosyası bir **çalışma
  girdisidir**, iş listesi değildir. Kuyruktaki "karar/not" sütunları RESUME çapası ya da
  `deferred-triggers.md` ile paralel bir açık madde listesine dönüşmemelidir; iş bitince açık kalanlar
  kanonik yere taşınır.
- **SAP'ye yazan** bir toplu işte bu sözleşme tek-yazıcı, reviewer pre-flight (ADR 0006) ve
  PULL-BEFORE-EDIT (ADR 0016) şartlarının **yerine geçmez**; onlara ek olarak uygulanır.
- Yazılacak araç paylaşılan çekirdeğe girecekse fixture'ı en az: geçerli kuyruk · bilinmeyen kimlik
  (KDS-3) · boş alan (KDS-4) · yeniden koşumda taşıma ve kimlik değişimi (KDS-5) vektörlerini içerir.

## İlgili

- [`howto-atc-duzeltme-kaliplari.md`](howto-atc-duzeltme-kaliplari.md) §5 (ilk olası kullanım: toplu ATC düzeltme)
- prior-art: yok — çekirdekte toplu model yargısını dosyayla dikmeye dair yazılı desen bulunamadı
  (çekirdek aramaları: "kuyruk dosya", "judgment", "yargı dosya" — yalnız ilgisiz eşleşme; 2026-10-12).
