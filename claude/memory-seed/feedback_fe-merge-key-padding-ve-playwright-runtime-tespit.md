---
name: feedback_fe-merge-key-padding-ve-playwright-runtime-tespit
description: İki SAP koleksiyonunu OrderItem ile merge ederken padding uyumsuzluğu (OPENITEM "10" vs façade "000010") sessiz tüm-null; "FE boş ama backend doğru" → playwright runtime tespiti
metadata:
  node_type: memory
  type: feedback
  originSessionId: 6b9195f9-e63c-4781-931d-b9672c867a85
---

2026-06-18, SIP_SE OrderPicker: "Gün Sayısı" penceresinde TÜM miktar kolonları (SiparisMiktari/TerminKum) boştu + "Uygula" etkisizdi. Kök sebep iki dersi birleştiriyor:

**1) Merge-key padding tuzağı (asıl bug):** İki SAP-kaynaklı koleksiyonu `OrderNo + "|" + OrderItem` string-concat ile merge ederken POSNR formatı UYUŞMAZ → sessiz %100 mismatch → eşleşmeyen alanlar null → UI boş. Burada: OPENITEM (OData entity, ZSD001_I_SE_A_OPENITEM) `OrderItem="10"` (sıfırsız) döndü; engine façade (GetOpenQty, ham VBELN/POSNR) `OrderItem="000010"` (6-hane padding) döndü. Fix: anahtarın sayısal parçasını HER İKİ tarafta normalize et — `keyOf=(no,it)=>no+"|"+parseInt(it,10)` (NaN'a ham-değer fallback). Aynı tuzak vbeln/posnr/matnr gibi her zero-pad'li alanda geçerli.

**2) "FE boş/yanlış ama backend doğru" → PLAYWRIGHT RUNTIME TESPİT:** Bu bug statik analiz + backend-doğrudan-çağrı ile YAKALANAMADI (engine izole doğruydu: GetOpenQty 0→0/20→400 doğru dönüyordu; FE kodu da "doğru görünüyordu"). Kullanıcı "playwright ile bakamaz mısın" dedi → local UI (8101) playwright ile sürüldü; `browser_evaluate` ile (a) `view.getModel("se").getProperty("/pickItems")` anahtarları + (b) `odata.callFunction("/GetOpenQty")` sonuç anahtarları okunup KARŞILAŞTIRILDI → "10" vs "000010" anında görüldü; normalize'lı merge canlı denenip 3000000005→sip400/term1000 KANITLANDI. Combobox/UI ile uğraşmadan controller'ı evaluate ile programatik sürmek (header set + onAddOrders + model oku) hızlı + kesin.

**Why:** İki tarafı da aynı SAP sisteminden geldiği için "format aynıdır" varsayımı yanlış — OData entity okuması conversion-exit uygular (sıfırsız), ham CDS/RAP façade uygulamaz (padded). String-concat merge bunu sessizce yutar; hiçbir hata/exception yok, sadece null. Ve bu sınıf bug runtime'da görünür: model katmanında veri var ama join üretmiyor → ne ABAP syntax check ne FE lint ne backend-call yakalar.

**How to apply:** (1) İki koleksiyonu key ile merge eden HER FE/ABAP join'de zero-pad'li alanları normalize et (parseInt veya iki tarafı da ALPHA/aynı formata getir) — bkz [[feedback_namespaced-dtel-ddl-tirnaksiz]] (benzer sessiz-düşme sınıfı). (2) "done"=runtime-doğrula ([[feedback_done-tam-kapsam-dogrula]], [[feedback_ui5-v2-plumbing-reuse-traps]]): "backend doğru ama UI boş/yanlış" raporunda TAHMİN etme → playwright ile local'i sür, `browser_evaluate` ile model + OData sonucunu oku/karşılaştır, aday-fix'i canlı dene. Token-verimli: snapshot/screenshot yerine `evaluate` ile sayısal oku ([[feedback_arastir-once-patinaj-uretim-gorev]]). (3) Expert UI'yi süremiyor (frontend-expert'te playwright yok) → runtime tespit/teyit LİDER işidir, sonra fix'i expert'e ver.
