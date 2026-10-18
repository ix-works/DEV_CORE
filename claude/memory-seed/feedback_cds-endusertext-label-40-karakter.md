---
name: cds-endusertext-label-40-karakter
description: "CDS @EndUserText.label annotation değeri en çok 40 karakter (SAP W: 'Type must be String(40)'); DDLS obje açıklaması (adtcore:description) 60 — ≤60 kontrolü etiket için YANLIŞ sınır"
metadata:
  type: feedback
  seed: evet
---

CDS `@EndUserText.label` annotation'ı **40 karakterle** sınırlı: aktivasyon hata değil **W** verir
(`Annotation value '...' length (N) too long. Type must be 'String(40)'`) ve değer OData/ön yüzde kesilebilir.
Obje başlığındaki etiket ayrıca `adtcore:description`'a (60 kr) tam yazılır — o yüzden "açıklama doğru" readback'i
annotation uyarısını GÖSTERMEZ. Etiket listesi üreten/kontrol eden adımda sınırı **40** al (60 değil).

**Why:** Bir projede, 2026-09-30 — backend-expert + bug-gate etiketleri "≤60" diye geçirdi, 12 objede 5 W çıktı
(3 başlık 42/42/49, 2 alan 42/49; alan etiketleri canlı kardeşten alıntıydı ve kardeşte de aynı uyarı vardı).
**How to apply:** CDS etiket önerisi/onay listesi hazırlarken ≤40 kr kontrolü; aktivasyon yanıtındaki W'leri ham gövdeden oku
(MCP `adt_activate` çoklu yolu W döndürmüyordu — yazıldığı tarihte).
Son-doğrulama: 2026-09-30 · Applies-to: s4_private 2025, CDS view entity + abstract entity. prior-art: yok (memory + core adt-cds/adt-rap "String(40)" araması 0).
