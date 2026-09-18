---
name: feedback_tek-seferlik-script-paylasilan-modulun-desenini-yeniden-turetmez
description: "Tek seferlik bir tarama/genericize script'i yazarken paylasilan modulun desenini yeniden turetme — o modulun yorumlari, senin dusecegin tuzaklarin kaydini tutar"
metadata:
  type: feedback
---

Bir kerelik bir tarama/dönüştürme script'i yazarken (genericize, sızıntı taraması, toplu
yeniden adlandırma) deseni **yeniden türetme**: projede o işi yapan paylaşılan modül varsa
**onu import et**. Gerekçe kod tekrarı değil — o modülün **yorumları, daha önce düşülmüş
tuzakların kaydını tutar**.

**Ölçülen vaka (2026-09-18):** 108 dersi public çekirdeğe tohumlarken kendi genericize
script'imi yazdım ve kelime-sınırı (`\b`) kullandım. Alt çizgi bir word-char olduğu için
`METOT_<ad>` biçimindeki her varyant **sessizce kaçtı** ve firma unvanları public repoya
girdi. Aynı tuzak `genericize_common.py`'nin **kendi `D3` yorumunda** yazılıydı:
*"`\bzsd0…` deseni ön-ekli adı kaçırıyordu"*. Yani ders **yazılıydı ve ben onu okumadım**,
çünkü modülü hiç açmadım — kendi desenimi sıfırdan yazdım.

**Neden ikinci kapı da tutmadı:** kimlik kapısının isim listesi o sınıfı içermiyordu. İki
bağımsız koruma katmanı vardı ama **ikisi de aynı boşluğa düştü** — her biri örtük olarak
*"öbürü yakalar"* varsayımıyla yazılmıştı.

⭐ **Asıl kural: redundans, katmanlar BAĞIMSIZ değilse redundans değildir.** İki kapıya
güveniyorsan, ikisinin **aynı** girdi sınıfında kör olup olmadığını ölç — "iki kapı var"
cümlesi bir güvence değil, bir hipotezdir.

⭐ **VAKA 2 — bağımlılık SONRADAN da doğabilir (2026-09-18 akşamı, Q329→Q330).** Vaka 1'de iki
katman **aynı anda** kördü. Bu ikincisinde biri düzeltildi ve **tam da bu yüzden** yeni bir
bağımlılık doğdu: sızıntı kapısının dosya-bazlı muafiyeti satır-bazlıya daraltıldı (commit kapısı
artık yakalıyor), ama **yazım anındaki** guard'ın aynı muafiyeti dosya-bazlı kaldı. Ölçüldü
(gerçek giriş noktası + pozitif kontrol): muaf dosyaya sentetik kimlik yazımı **rc=0 sessiz**,
aynı içerik muaf olmayan dosyaya **rc=2 BLOK**.

Sonuç *"risk düşük, öbür katman yakalıyor"*dur — ama bu cümle **tam olarak Vaka 1'in cümlesidir**.
Fark şu: artık bağımlılık **tek yönlü ve yazılı**. Düzeltilen katmanın muafiyeti yarın yeniden
genişlerse ikisi **birlikte** körleşir ve kimse fark etmez, çünkü ikinci katmanın körlüğü
*"zaten öbürü bakıyor"* diye kabul edilmişti.

⛔ **Alt-ders: bir katmanı düzeltmek, öbürünün körlüğünü MEŞRULAŞTIRMAZ — onu GÖRÜNMEZ kılar.**
Bir kapıyı daralttığında, aynı sınıfın **kardeş yüzeylerini** aynı turda ara ve bulduğunu
*kapatmasan bile* kaydet; kaydın içine **hangi katmana yaslandığını** açıkça yaz, yoksa o
yaslanma bir sonraki turda görünmez bir varsayıma döner.

**Why:** public repoya giden yayın **geri alınamaz** (cache'lenir, geçmişte kalır). Bu vakada
HEAD temizlendi ama git geçmişi temizlenmedi; geçmiş yeniden yazımı ayrı ve maliyetli bir karar.

**How to apply:**
- Tek seferlik script yazmadan önce sor: **"bu işi yapan paylaşılan bir modül var mı?"** Varsa
  import et; yoksa bile **önce onun yorumlarını oku** (tuzak kaydı oradadır).
- Desenini kendin yazmak zorundaysan, paylaşılan kapıdan **DAR olmadığını** ölç — dar bir
  ön-tarayıcı "temiz" der ve yanlış güven üretir.
- İki katmanlı korumada, **ikisini aynı negatif vakayla** test et; ikisi de kaçırıyorsa
  koruma tek katmanlıdır ve o katman da yok.
- İlgili: [[feedback_kapi-tek-tarayicidan-ibaret-degildir]] ·
  [[feedback_yesil-regresyon-suiti-duzeltmenin-kaniti-degildir]] ·
  [[feedback_kapsam-niteleyicisini-dusurme]]
