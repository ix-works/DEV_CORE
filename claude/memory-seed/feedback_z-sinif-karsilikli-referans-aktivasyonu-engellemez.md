---
name: feedback_z-sinif-karsilikli-referans-aktivasyonu-engellemez
description: "İki Z sınıfı birbirine kod düzeyinde referans verse de (A→B sabit, B→A metot çağrısı) yalnız bir taraf değişirken aktivasyon SORUNSUZ — ölçüldü; \"aktivasyon sırası kilitlenir\" şerhi kanıtsızdı"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a07fcbe5-7d7b-4e12-acfd-1f1addd0e07d
---

ZSD001'de `ZCL_SD022_IDOC_PARSER` zaten `ZCL_SD022_PROCESSOR=>c_status` okuyordu; 2026-09-15'te PROCESSOR implementation'ına `NEW zcl_sd022_idoc_parser( )->reparse( )` statik çağrısı eklendi (pakette ilk karşılıklı referans). Gateway PROCESSOR'ı TEK BAŞINA push+activate etti → `[OK] activated`, canlı=repo readback, `adt_inactive_objects`=0. Pakette `ZCL_SD022_MAIL.clas.abap:170-172` "aktivasyon sırası birbirine kilitlenirdi" diyerek bu deseni bilerek kaçınıyordu — o şerhin arkasında ölçüm yoktu.

**Why:** Döngüden korkup dinamik `CALL METHOD`'a kaçmak where-used zincirini koparır ve ad/imza hatasını çalışma zamanına iter; statik çağrı denenmeden bu bedel ödenmemeli.

**How to apply:** Karşılıklı referans gerekiyorsa önce statik çağrıyı yaz, DEĞİŞEN sınıfı tek başına aktive et (öteki zaten aktif olsun), readback ile doğrula; başarısızsa dinamik çağrıya geç. ⚠ Kanıtın SINIRI: iki sınıfın AYNI anda yeni yaratılıp aynı partide aktive edilmesi ve boş hedefe (QA/PRD) aynı TR'de ilk importu ÖLÇÜLMEDİ — taşımada ikisi aynı TR'de gitmeli.

Son-doğrulama: 2026-09-15
Applies-to: s4_private ABAP source-based class (ADT push), tek taraf değişikliği
prior-art: yok (70 Z sınıfında karşılıklı çift 0; standart emsal CL_ABAP_TYPEDESCR↔STRUCTDESCR kalıtım üzerinden)
