---
name: feedback_cdn-surum-varligi-surum-dosyasiyla-kanitlanmaz
description: UI5 CDN'de bir sürümün kullanılabilirliği sap-ui-version.json 200 ile KANITLANMAZ — kütüphane dosyaları 404 olabilir; kanıt kullanılacak kütüphanenin kendisidir
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

Bir SAPUI5 sürümünün CDN'de (`ui5.sap.com/<sürüm>/resources/`) kullanılabilir olduğunu `sap-ui-version.json` dosyasının 200 dönmesiyle kanıtlama. Bu dosya 200 dönerken kütüphane dosyaları (`sap/m/library.js` vb.) 404 olabilir.

**Why:** Vaka 2026-11-06: lider, maketi hedef sistemin UI5 sürümüyle (bir 1.120.x yaması) üretmek istedi ve yalnız sürüm dosyasını ölçtü (200), sonra sürümün "var" olduğunu söyledi. Frontend ajanı bootstrap sırasında kütüphanelerin 404 döndüğünü buldu ve maket aynı 1.120 hattının erişilebilir başka bir yamasıyla üretildi. Ölçüm yanlış yüzeye bakmıştı: sürüm dosyasının varlığı kütüphanelerin dağıtıldığı anlamına gelmez.

**How to apply:** CDN'den sürüm seçerken uygulamanın kullanacağı kütüphane dosyalarından en az birini (`sap/m/library.js`, `sap/ui/core/library.js`) GET ile ölç. Bootstrap'ı gerçek giriş noktasından doğrula: tarayıcıda yükle ve konsoldaki 404 sayısına bak. Aynı yama hattında erişilebilen en yakın sürümü seç ve gerekçesini kayda yaz.

**Kapsam:** bu ders yalnız CDN'den yüklenen **maket ve yerel çalıştırma** içindir. Teslim edilen uygulama UI5'i CDN'den YÜKLEMEZ. `index.html` backend'in kendi kopyasını kullanır ve CDN pin'i YASAKTIR (checklist `UI-BOOT-01`, `FE-53`; sürüm ve tema backend'den ölçülür). Bu ders o kuralı gevşetmez. Maket için seçilen CDN sürümü teslim edilen `manifest.json`'a taşınmaz.

Son-doğrulama: 2026-11-06 · Applies-to: freestyle UI5 maket/yerel çalıştırma, CDN bootstrap
