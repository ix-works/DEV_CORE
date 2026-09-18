---
name: kapi-tek-tarayicidan-ibaret-degildir
description: "Bir kapının neyi yakaladığını ölçerken TEK yardımcı fonksiyonu denemek kapı hakkında hüküm vermez — kapı birden çok tarayıcıdan oluşabilir; ölçümü kapının GİRİŞ NOKTASINDAN yap"
metadata: 
  node_type: memory
  type: feedback
---

Bir kapının (`pre-commit`, guard, validator) *"şunu yakalıyor mu"* sorusunu, kapının
kullandığı **tek bir yardımcı fonksiyonu** çağırarak cevaplama. Kapı birden çok tarayıcının
**birleşimi** olabilir; birini ölçüp kapının tamamı hakkında hüküm vermek yanlış güvence üretir.

**Ölçülmüş vaka (2026-09-17):** `core_precommit`'in paket adlarını yakalayıp yakalamadığını
ölçmek için `genericize_common.id_pattern()`'a sonda gönderdim → `ZSD0xx`, müşteri adları
*"serbest"* çıktı. Kullanıcıya *"kapı bunları yakalamıyor, genericize'ı elle yapmam gerek"*
diye **yanlış bilgi verdim**. Gerçekte kapının **ayrı bir Z-obje kuralı** vardı
(`Z_OBJ_PAT` + `ORNEK_Z` beyaz listesi, yalnız `ZSD000`/`ZSD001` serbest): commit ilk
denemede **132 ihlalle** bloklandı ve 108 dosya baştan üretilmek zorunda kaldı.

**Simetrik ders — kapı yeşilse de kapsamına bak:** aynı kapının Z-obje deseni
`Z[A-Z]{2}\d{3}` arıyor; **4 harfli** bir ad (`ZMOD001` biçiminde — temsilî) ondan **kaçıyor** (ölçüldü).
*(Not: bu desen sonradan 2-4 harfe genişletildi — `genericize_common.py` D7, 2026-09-18.)*
Yani kapı hem sandığımdan geniş hem de sandığımdan dardı — iki yönde de tek sondayla
bilinemezdi.

**Why:** *"Kapı yakalamıyor"* bir **sınıf iddiasıdır** ve tek bir fonksiyon çağrısı onu
kanıtlamaz; çekirdeğin *"ölçümü GERÇEK GİRİŞ NOKTASINDAN yap"* kuralının kapı-yüzeyindeki
karşılığıdır. Yanlış yön pahalı: "yakalamıyor" derken gereksiz elle iş üretir, "yakalıyor"
derken gerçek sızıntıyı serbest bırakır.

**How to apply:** (1) Kapıyı **kendi giriş noktasından** koş — sentetik payload ile
(`python <gate> < payload.json`), tek yardımcı fonksiyonla değil. (2) Yakalamayı iddia
edeceksen **pozitif kontrol** koş: bloklaması beklenen bir örnek gerçekten bloklanıyor mu.
(3) Kapının **kapsam sınırını** da yaz — neyi yakalamadığı, yakaladığı kadar önemlidir.
İlgili: [[feedback_kapinin-var-olmasi-her-girdi-yolunda-calistigi-degildir]] ·
[[feedback_exit0-degil-cikti-kaniti]] · [[feedback_hicbir-yerde-yok-demeden-once-nerelere-baktigini-yaz]]
