---
name: feedback_create-cds-view-xml-escape
description: "Yeni CDS yaratırken create_cds_view source'u XML'e escape etmeden gömüyordu → <>/</& 'Unknown error'; fix html.escape; ayrıca read-only consumption=select from (projection değil)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 8c1257a6-fbd9-48f4-9ef0-5040be6f1540
---

Yeni CDS yaratma kanonik akışı: **`create_cds_view` (shell) → `push_object` (gerçek source + activate)** (push_object source endpoint'i text/plain, `<>` sorunsuz). 2026-06-11 ZSD001_I/C_MAT_LOOKUP'ta 3 tuzak:

1. **`create_cds_view` XML-escape bug'ı:** create POST gövdesi `<ddl:source>{cds_source}</ddl:source>` — source'u RAW gömüyordu. `case when x <> 0` gibi `<`/`>`/`&` içeren source XML'i bozuyor → SAP reddediyor → retry-wrapper "Request failed after 3 retries: **Unknown error**" (gerçek hata gizli) → object yaratılmaz → push_object `[423] not locked`. `<>` içermeyen view'lar (ör. basit agregasyon) escape gerektirmediği için çalışmıştı. **FIX uygulandı:** `sap_adt_lib.create_cds_view` → `html.escape(cds_source, quote=False)`. (T12 template-port adayı.)

2. **Opaque hatada yöntem değiştirme — önce gerçek hatayı yakala.** create_cds_view → minimal shell → MCP post_shell diye dolandım (kullanıcı uyardı). Doğrusu: ham `session.post` ile `status_code + response.text` yazdır → XML break anında görünür. [[feedback_playbook-once-oku]] (tahminle deneme yok, çalışan yöntemi koru).

3. **Read-only consumption = `as select from`, `as projection on` DEĞİL.** `as projection on <I>` → "Transactional Projection View must be part of a business object" (projection = RAP transactional, BDEF/BO ister). Salt-okunur OData lookup için `define view entity ... as select from <I_view>` + `@Semantics` tekrar bildir. Ayrıca `define root ... as projection on <non-root>` → "ROOT keyword not valid". Detay: playbook/adt-cds.md "CDS Yaratma Tuzakları".
