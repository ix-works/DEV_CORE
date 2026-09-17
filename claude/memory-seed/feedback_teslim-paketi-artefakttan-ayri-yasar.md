---
name: feedback_teslim-paketi-artefakttan-ayri-yasar
description: "Dışarı gönderilen paket (zip/ek) çalışma ağacındaki artefaktın kopyasıdır — göndermeden ÖNCE paketin İÇİNİ ölç, dosyayı değil"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 99a370d4-a293-4939-b68e-77dcd19e7d93
---

Bir artefaktı doğrulamak, o artefaktın **paketlenmiş kopyasını** doğrulamaz. Paket ayrı bir
yaşam sürer: bir kez kurulur, sonra kaynak dosya değişir, paket eskir — ve **hiçbir kapı paketi
görmez**.

**Vaka (2026-08-25, ZSD001 <MUSTERI-D> CPI):** kullanıcı 14:46'da `VOLVO_V8.zip` kurdu; düzeltme ajanı
14:50'de `.mmap`'i yazdı. Zip eski dosyayı taşıyordu (`634ad7c5…`, `context=9`, `E1EDP36` açık),
canlı dosya yenisini (`d9569376…`, `context=11`, `E1EDP36` kapalı). Eşlik eden not *"E1EDP36
kapattık, context ekledik"* diyordu. Gönderilseydi karşı taraf **tam tersini** taşıyan dosyayı
alacak ve nota bakıp değişikliğin yapıldığını sanacaktı. Bug-gate yakaladı; ben `.mmap`'i üç kez
ölçmüştüm ama **zip'e hiç bakmamıştım**.

**Kural:** teslimden önce paketin İÇİNİ aç, her üyenin hash'ini canlı dosyayla karşılaştır.
`ls -l` yetmez (V7 ile V8 aynı boyuttaydı, yalnız üye sırası farklıydı).

**Nasıl uygula:**
- Paketi **teslim anında** canlı dosyalardan yeniden kur — "zaten kurmuştum"a güvenme
- Açıp üye üye `md5` al, çalışma ağacındakiyle **eşitliğini ölç**
- Beklenen hash'i **eşlik eden nota yaz** — karşı taraf import öncesi doğrulayabilsin
- Eski paketleri sil; aynı klasörde duran `V7`/`V8`/`V9` yanlış olanı gönderme riskidir

Bu, [[feedback_kanit-tazeligi-indeks-ve-zaman-sirasi]]'nın teslimat ayağı: orada ölçümün zaman
sırası, burada **ölçülen nesnenin kimliği** kayıyor. Aynı aile: [[feedback_sonucu-olc-uygulamayi-degil]].
