---
name: feedback_belge-uygulama-ortak-ui-sablonu
description: Tüm belge-işleyen uygulamalar aynı UI şablonu — List(filtre+akordion)→başlık+kalem
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 791c30b9-6728-4e20-94d7-8d4a14484d2d
---

Kullanıcı kararı (2026-06-14): ZSD001'teki **tüm belge-işleyen uygulamalar aynı/benzer UI layout'unu** kullanır — ayrı uygulamalar olsalar bile:
- **1. ekran:** filtre + akordion liste (mevcut belgeler).
- **2. ekran:** başlık + kalem (Yarat/Değiştir).
- Akış: **Liste → Yarat → Değiştir** (FIT_SE deseni, kanonik şablon).

Uygulanır: FIT_SE, SIP_SE, IHR_SE (kalem=sevk emri kalemleri) ve **Booking** (ayrı uygulama; kalem = konteynerler). Her uygulamanın BO/servisi farklı olabilir; UI şablonu/etkileşim deseni ortaktır.

**Why:** Tutarlı kullanıcı deneyimi + tekrar kullanılabilir UI deseni; her belge uygulaması sıfırdan farklı layout tasarlanmaz.

**How to apply:** Yeni belge-işleyen uygulama UI'si tasarlarken FIT_SE şablonunu baz al (List filtre+akordion → başlık+kalem). Grid liste standardı (ADR 0008) + freestyle PRE-FLIGHT da geçerli. İlgili: [[feedback_grid-liste-standardi]] · [[feedback_liste-ekrani-alv-standardi]] · [[project_sprint-plan-rap-revize]].
