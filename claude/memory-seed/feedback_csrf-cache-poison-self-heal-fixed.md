---
name: feedback_csrf-cache-poison-self-heal-fixed
description: "CSRF cache-poison patinajı (3x 403 → fail) KÖK-FİX edildi 2026-06-14 — artık otomatik self-heal, elle .csrf_token.json silmek gerekmez"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 791c30b9-6728-4e20-94d7-8d4a14484d2d
---

`sap_adt_lib.py` CSRF cache-poison patinajı **2026-06-14 kök-fix edildi**.

**Kök sebep (2 kat):** (1) `_retry_request` CSRF retry'da `fetch_csrf_token(force_refresh=True)` çağırıyordu AMA çağıran fonksiyonların (create_cds_view vb.) `make_request` closure'ı header'ı DIŞ kapsamda 1 kez kuruyordu → her retry AYNI bayat token'ı yolluyordu → 3x 403 "CSRF token validation failed" → fail. (2) `_request_with_csrf_retry` poison on-disk cache'i temizlemiyordu.

**Fix:** (a) create_cds_view (+create_dataelement zaten doğruydu) closure'ı header'ı İÇERİDE yeniden kuruyor → refresh edilen token gidiyor. (b) `_request_with_csrf_retry` 403+("CSRF" veya `x-csrf-token: Required`)'te `fetch_csrf_token(force_refresh=True)` (cache temizleme dahil) + retry. (c) BDEF create artık `_request_with_csrf_retry` üzerinden.

**Why:** Spike'ta her CSRF 403'te elle `.csrf_token.json` silmek gerekiyordu — yavaşlık + her seferinde tekrar.

**How to apply:** Yeni create/push fonksiyonu yazarken **`_request_with_csrf_retry`** kullan VEYA `_retry_request` + closure'da header'ı İÇERİDE kur (dışarıda değil). Poison cache testiyle doğrulandı (create_cds_view + create_behavior_definition: bogus token → 1 retry → success). Elle cache silmeye artık gerek yok. Bağlı: [[feedback_create-bdef-script-broken-use-blues-recipe]] [[feedback_adt-dtel-create-fixed]].
