---
name: feedback_kaydin-onerdigi-fix-yonu-de-bir-iddiadir
description: "Eski bir bulgu kaydının ÖNERDİĞİ düzeltme yönü de doğrulanmamış bir iddiadır — kaydın KENDİ gövdesindeki ölçüm ile bugünkü ölçümü birleştirmek çoğu zaman yeni ölçümden daha keskin sonuç verir (2026-08-29 #75: 'sıra yanlış' önerisi çürütüldü, kök neden 'yanlış sürümün ETag'i' çıktı)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f911c8cf-83f3-4ff2-bd38-ae5ee4790ae5
---

⛔ Bir kuyruk/bulgu kaydı iki ayrı şey taşır: **ölçüm** (ne gözlendi) ve **öneri** (nasıl
düzeltilmeli). Ölçüm kanıtlıdır; **öneri, kaydı yazanın o anki hipotezidir** ve çoğu zaman
hiç doğrulanmamıştır. Kaydı kapatırken öneriyi **talimat gibi** uygulamak, çalışan davranışı
bozabilir.

**Vaka 2026-08-29 (`#75`):** kayıt *"ETag alma sırası yanlış, sırayı tersine çevir"* diyordu.
Ama **kaydın kendi gövdesi** şunu da yazıyordu: *412'nin gövdesinde beklenen ETag zaten dönüyor*
(`…0013…` alınmış, `…0003…` isteniyor) ve *tekrar denemede 200 geliyor*. Bugün canlı ölçüldü:
`?version=inactive` isteği **tam da beklenen** ETag'i veriyor. İkisi birleştirilince kök neden
çıktı: sorun **SIRA değil, YANLIŞ SÜRÜMÜN ETag'i**. ⇒ Önerilen fix uygulansaydı **çalışan** bir
akış bozulacaktı. Kayıt gövdesi düzeltildi, `[DOĞRULANMADI]` damgası konuldu (ölçüm farklı
objeler üzerindeydi).

**Why:** Kayıtlar zamanla **talimata dönüşür** — özellikle toplu kapanış turlarında, uygulayıcı
kaydı okuyup önerisini uygular. Öneri yanlışsa hata **kaydın otoritesiyle** mühürlenir ve bir
daha sorgulanmaz. Ayrıca: kök nedeni bulmak için **her zaman yeni ölçüm gerekmez** — kaydın
kendi gövdesindeki gözlem, güncel bir ölçümle **sentezlenince** yeterli olabilir; bu hem ucuz
hem de kaydın çelişkisini görünür kılar. İlişkili:
[[feedback_onay-da-bir-iddiadir-mekanizmayi-olcmeden-net-deme]] ·
[[feedback_ajan-bulgusu-dogru-mekanizmasi-yanlis]] (bulgu doğru, mekanizma yanlış olabilir).

**How to apply:** Bir kaydı kapatmaya oturduğunda gövdesini **ikiye ayır**: hangi cümle
**ölçüm**, hangi cümle **öneri**? Öneriyi uygulamadan önce *"bu öneri doğruysa, kaydın kendi
ölçümü ne söylerdi?"* diye sor — çelişiyorsa **öneri değil ölçüm kazanır**. Yeni ölçüm yapmadan
önce kaydın kendi verisini oku; çoğu zaman cevap oradadır. Öneriyi çürüttüğünde gövdeyi
**düzelt** (silme, üzerine şerh düş) ve doğrulama sınırını açıkça yaz.
