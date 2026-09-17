---
name: feedback_kardes-taramasi-spawn-oncesi-kapsama-alinir-kuyruga-yazilmaz
description: "Kuyruk maddesi düzeltilmeden ÖNCE kardeş dosya taraması yapılır ve aynı sınıftaki vakalar KAPSAMA alınır; ajana \"kardeşleri raporla, düzeltme\" dersen kuyruk hiç yakınsamaz"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: cca08bdf-c505-460c-a1ba-8d1635bd8f7c
---

**Kural (kullanıcı, 2026-09-13):** Kardeş dosyada aynı hatanın olup olmadığı **düzeltme başlamadan
önce** kontrol edilir — lider triajda (grep dakikalar sürer) ya da ajan ilk adımında — ve bulunan
aynı-sınıf vakalar **o maddenin kapsamına alınır**. Sonradan kuyruğa yeni kayıt olarak yazılmaz.
Kullanıcının cümlesi: *"kardeş dosyaları ajan kontrol edip bulabiliyorsa sende bulabilirsin … bu
şekilde kuyruk hiç bitmiyor."*

**Why:** Ölçüldü (2026-09-13 turu): 7 madde kapandı, aynı sürede 10 yeni açıldı. Yeni kayıtların
çoğu fix ajanlarının "sınıf envanteri — düzeltme, raporla" talimatıyla yazdığı kardeş vakalardı
(Q318'in DELETE hatası → lock_objects/tables/dataelements/cds_exists = 3 yeni kayıt). Brif küçük PR +
paralel ajan çakışmasını önlemek için böyle kurulmuştu; bedeli kuyruğun yakınsamaması oldu. Kaynak
ölçümü: bu kardeşlerin kodu 2026-07-08 ilk içe aktarmadan geliyordu (infra üretmemişti) — yani
turdan önce grep ile bulunabilirdi.

**How to apply:**
1. Spawn öncesi: kaydın kusur desenini core'da `path=core/` ile tara; eşleşmeleri brife "KAPSAM:
   şu N dosya" diye yaz. Kapanış kanıtı tarama = kalıntı 0 ([[feedback_bulgu-listesi-ornektir-sinif-duzeltmesi-tarama-ister]]).
2. Taşınan şey düzeltme değil YÖNTEM — her kardeşte mekanizma ayrıca ölçülür
   ([[feedback_ayni-sinif-ayni-duzeltme-degildir]]).
3. Ajan çalışırken yeni kardeş bulursa: aynı desen + kendi dosya kümesindeyse AR-1'de bildirip
   KAPSAMA alır; yalnız başka ajanın uçuştaki dosyasındaysa ya da farklı sınıfsa kayıt yazılır.
4. Kozmetik yan bulgu (etiket/başlık/hijyen, hüküm ve SAP etkilenmez) kayda yazılmadan önce
   "riske değer mi" süzgecinden geçer.

Son-doğrulama: 2026-09-13 · Applies-to: infra kuyruğu turları (DEV_CORE), fix-ajanı brifleri
