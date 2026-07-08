---
name: feedback_arac-basarisizligini-zararsiz-sayma
description: "Bir araç çağrısının (activate/push) BAŞARISIZ dönüşünü 'beklenen/zararsız/include-doğası' diye geçiştirme; canlı state'i doğrula"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 1420ec34-9257-4b0a-aef4-aee509c5b810
---

Bir SAP araç çağrısı (özellikle `adt_activate`, `adt_push_source`) **başarısız** döndüğünde, onu "bu normal / beklenen / obje-doğası gereği" diye rasyonalize edip GEÇİŞTİRME. Gerçekten başarısız olduysa kod CANLI DEĞİLDİR.

**Somut tuzak (2026-06-22):** Gateway, exit Z-include `ZSD000_I_50MOVE_FIELD_TO_LIPS` için `adt_activate` "REPORT/PROGRAM statement missing / type INCLUDE" hatası verince bunu *"include'lar standalone aktive edilmez, beklenen davranış"* diye sınıfladı; lider de sorgulamadan kabul etti. **YANLIŞ** — exit/customer include'ları aktive EDİLİR/edilmeleri gerekir; kullanıcı elle aktive etmek zorunda kaldı. "Push edildi, source kalıcı" ≠ "aktif/canlı".

**Why:** Bu, [[feedback_ajan-olumsuz-donusu-kanitla-sorgula]]'nın AYNASI: orada "yapılamaz" negatif dönüşünü sorgula deniyor; burada bir BAŞARISIZLIĞIN "zararsız" pozitif çerçevelemesini sorgula. İkisi de "activated/uploaded/çalıştı mesajına güvenme" (CLAUDE.md çekirdek davranış) + [[feedback_done-tam-kapsam-dogrula]] ile aynı kök: canlı state'i KANITLA.

**How to apply:** Araç "başarısız" derse → (1) "beklenen" deme, DUR; (2) gerçek aktivasyon/varlık state'ini canlı readback ile doğrula (active vs inactive, sadece HTTP-200/source-var değil — bkz. [[feedback_inactive-worklist-audit-http200-degil]]); (3) gerçekten gerekiyorsa doğru yolu araştır (örn. exit-include aktivasyonu) veya kullanıcıya net flag'le; (4) "kalıcı ama aktif değil" durumunu ASLA "tamam" sayma.
