---
name: once-yuzey-taramasi-sonra-is-listesi
description: "Çok katmanlı işte (BE+FE+veri) önce TÜM yüzeyi tara, matris/iş listesi çıkar; katmanları sırayla keşfetme"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e424a095-8518-4681-bef7-a113d21aa4c0
---

Çok katmanlı bir iş (backend kuralı + FE yolu + veri) geldiğinde **önce yüzeyin tamamı
taranır ve tek bir matris/iş listesi çıkarılır**; sonra o listeden ilerlenir. Katmanları
sırayla keşfetmek (önce BE'yi düzelt → sonra FE'nin onu hiç çağırmadığını fark et → sonra
aynı desenin başka app'lerde olduğunu fark et → sonra bir yerde BE kuralının hiç olmadığını
fark et) işi günlere yayar.

**Why:** Kullanıcı geri bildirimi (2026-07-29, <PAKET-B> silme guard'ları): *"neden bu kadar
uzadı, neden tek tek yapıyorsun, şu kontrolleri tek seferde yapıp bir iş listesi halinde
ilerletmen gerekmiyor mu?"* — Haklıydı. İş dünden beri sürüyordu ve uzamanın sebebi ajan
sayısı ya da doğrulama titizliği değil, **hiçbir noktada tam yüzey taraması yapılmamış
olmasıydı.** "13 doğrulama metodunun her biri için: BE kuralı var mı + kablolu mu + FE o
yola gidiyor mu + mesaj belge numarası taşıyor mu" bir matristir ve tek oturumda çıkarılabilirdi.

**How to apply:** İş çok katmanlıysa (BE+FE, veya birden çok app/paket), build'e başlamadan
önce kapsam taramasını **paralel fan-out** ile yaptır (ör. bir ajan BE envanteri, bir ajan
FE envanteri) ve çıktıyı **matris** olarak iste — her hücre kaynak/canlı kanıtla dolsun,
emin olunmayan hücreye "DOĞRULANAMADI" yazılsın. Sonra o matristen iş listesi üret, sırayla
kapat. Tarama maliyeti bir turdur; keşfetmenin maliyeti her katmanda bir tur.

İlgili: [[kararlari-once-topla-sonra-dispatch]] (build-unit içi kararlar) ·
[[done-tam-kapsam-dogrula]] ("tamam" demeden önce kapsam) ·
[[fix-oncesi-where-used-blast-radius]] (değişen objenin etkisi) ·
[[subagent-karar-kurali]] (paralelleşen iş → fan-out)
