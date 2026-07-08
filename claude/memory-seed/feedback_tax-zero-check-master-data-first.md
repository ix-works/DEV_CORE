---
name: feedback_tax-zero-check-master-data-first
description: "App-yaratılan siparişte KDV/MWST=0 → ÖNCE müşteri ana-kayıt vergi sınıflandırmasına bak (vergisiz/0 seçili olabilir), EML/RAP create veya pricing kodunu suçlamadan"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 8c1257a6-fbd9-48f4-9ef0-5040be6f1540
---

SD siparişinde **KDV/MWST tutarı 0** veya MWST koşulu PRC_ELEMENT'te hiç yok ise → **ÖNCE müşteri ana-kayıt vergi sınıflandırmasını (KNVI / CustomerTaxClassification) kontrol et.** "Vergisiz / 0" seçiliyse pricing MWST'yi 0 belirler (ya da koşul hiç düşmez) — bu **master data**, kod değil.

**Why:** 2026-06-11 ZSD001 app-yaratılan siparişlerde (1000000029/030) KDV=0 geldi. EML `I_SalesOrderTP` create (BAPI_SALESORDER_CREATEFROMDAT2 halefi), DY belirleme exit'i, "yeniden-fiyatlandırma type G" diye uzun araştırıldı. Gerçek sebep: **müşterinin vergi parametresi yanlıştı (vergisiz 0 seçili)**, kullanıcı master'ı düzeltince yeni siparişler KDV'yi sakladı. Boşa giden zaman: EML/pricing kodu doğruydu (aynı kodla daha eski sipariş 1000000028 vergi getirmişti).

**How to apply:** Tax/pricing anomalisinde teşhis sırası: (1) iki örnek belge KIYASLA — biri çalışan biri bozuk (CreatedBy/tarih/master alanları); (2) **master data önce** (müşteri vergi sınıfı, malzeme vergi sınıfı, plant ülkesi); (3) ancak sonra create/EML/exit kodu. "Aynı kodla eski belge çalışıyorsa kod suçsuzdur → veri/config değişmiştir." API ile read-only kıyas (A_SalesOrder/A_SalesOrderItem tax alanları) hızlı ayırt eder. İlişkili: [[feedback_<legacy_source>-field-adlari-sistem-bagimli]].
