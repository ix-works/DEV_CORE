---
name: freestyle-ui-preflight
description: Yeni freestyle UI5 (OData V2/RAP) yazmadan önce ui-freestyle-odata-v2.md §0 PRE-FLIGHT + checklist zorunlu
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 08868cc7-ead9-4d38-b6fe-2fd1fd3eb04c
---

Yeni bir freestyle UI5 (OData V2 / RAP tüketen — ORDER_ORDER gibi)
geliştirmesine başlamadan **önce** `playbook/ui-freestyle-odata-v2.md`
§0 PRE-FLIGHT'ı ve `playbook/checklists/ui-freestyle-creation.md`'i oku ve
baştan uygula.

**Why:** ORDER — görece basit bir uygulama — UI tarafında aşırı patinaj
yaptırdı (value-help seçimi yansımıyor, kod gelir ad gelmez, kaydet
feedback'i gelmez, "Liman Ekle" geç gelir, RAP lock "bloke" mesajı, V2
createEntry deferred vs create anında, TablePersoController jQuery Deferred,
CHAR1↔CheckBox). Kullanıcı bunların tecrübe olarak kalıcılaşmasını ve
sonraki programlarda tekrarlanmamasını açıkça istedi (2026-05-15).

**How to apply:** Editable child grid varsa EN BAŞTAN JSON edit-buffer
mimarisi kur (V2 nav-binding+createEntry ile editable grid YAPMA). Save
şablonu: blur→setTimeout(0)→isNew?deepCreate:(headerMERGE+child C/U/D)→
_runSeq SIRALI→tek _ok/_err; hasPendingChanges gate kullanma. Numeric/date
binding'e OData type; value-help kontrole DİREKT yaz + <X>Name CDS expose.
Backend/ADT tarafı bu kapsamda DEĞİL → o [[feedback_playbook-once-oku]] / adt-rap.md
§32 (early numbering + MCP lock-cache orada). Bağlı: [[feedback_yeni-teknoloji-once-kural-seti]].
