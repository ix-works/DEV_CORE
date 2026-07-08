---
name: feedback-ponumber-posnumber-global-iptal
description: "ZSD001 SEVKEMRI projesinde PONUMBER + POSNUMBER alanları tüm struct'larda iptal (TD spec \"korunan\" diyorsa bile)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7091c15c-424a-42a9-bcf8-7c3f51f36d33
---

ZSD001 SEVKEMRI projesinde **PONUMBER** ve **POSNUMBER** alanları tüm struct'larda **iptal** edilmiştir. Bu kural ORDER_ORDER_IT, ORDER_SHIPMENT ve diğer struct'lar için aynı şekilde geçerli.

**Why:** Karar 2026-05-14'te ORDER_ORDER_IT için verildi. Kullanıcı "bu 2 alan iptal ettiğimiz alanlar muhtemelen" demesi üzerine globalleştirildi. Kaynak <LEGACY_SOURCE> Z DTEL'leri (`ZSD_071_D_PONUM`, `ZSD_D_POS_NUMBER`) farklı paketlerden geliyor ve <PROJECT_NAME> scope'una alınmıyor. Sales order konvansiyonu ile çakışıyor.

**How to apply:** Sprint 6 struct yaratımında her struct için (ORDER_ORDER_IT, ORDER_SHIPMENT, vs.) `--skip-fields` listesine `ponumber,posnumber` mutlaka eklenir. TD spec markdown'ında "korunan" listesinde olsa da uygulanmaz. CDS güncellemelerinde de bu 2 alan kullanılmaz (ZSD001_DDL_ORDER_ORDER_IT örneği: 2026-05-14, PONumber satır 30 silindi).

İlgili: [[feedback_zli-obje-text-tahmin-yasak]]
