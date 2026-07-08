---
name: resolved-tooling-bugs
description: "Çözülmüş MCP/sap_adt_lib tooling-bug'larının konsolide kaydı; kök-fix kodda, yalnız regresyon teşhisi için referans"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d6233272-ea94-4d94-bc1d-56e619f9dc11
---

10 tooling-bug kök-fix'i **koda yazıldı + /mcp restart sonrası stabil**. Bu kayıt yalnız **regresyon olursa "ne bozuktu + nasıl çözüldü"** referansı içindir — günlük işte bunlara dikkat etmeye gerek yok. Derin detay için her satırın linkli orijinal dosyasına bak.

**Why:** Bu 10 kayıt index'te tam-metin tutulduğunda MEMORY.md'yi şişiriyordu; fix kodda olduğu için index'te tek-satır yeterli (gate-testi: kod-fix var → konsolide).
**How to apply:** Bir MCP/ADT aracı eskisi gibi tekrar bozulursa ilgili maddeye bak; fix'in kodda hâlâ duruyor mu diye doğrula.

- **adt_dtel_create** → DTEL domain-binding bug kök-fix 2026-06-14 (blue:wbobj + dtel:dataElement + _get_domain_typeinfo). Bkz. [[feedback_adt-dtel-create-fixed]]
- **adt_get DDIC okuma** → XML-DDIC'i `exists:false` dönüyordu; kök-fix 2026-06-16 atom.py→get_ddic_object. Bkz. [[feedback_adt-get-ddic-read-fixed]]
- **adt_get namespace-encode** → slash'lı obje adı encode edilmiyordu (yanlış 404); fix `quote(safe='')`. 404→adt_search çapraz-doğrula. Bkz. [[feedback_adt-get-namespace-encode-trap]]
- **source-drift name-collision** → aynı-ad farklı-tip sahte drift; fix object_type filtresi; M1 block kaldırıldı (type-fix artık pull yolunda). Bkz. [[feedback_source-drift-name-collision-fixed]]
- **create_behavior_definition** → script bozuktu; çözüm blues.v1 reçetesi (adt-rap §32.6c): /bo/behaviordefinitions + blue:blueSource + LOCK/PUT/UNLOCK; BDEF+class birlikte aktive. Bkz. [[feedback_create-bdef-script-broken-use-blues-recipe]]
- **CSRF cache-poison** → 3x 403 patinajı; fix _request_with_csrf_retry force-refresh + cache temizlik (elle .csrf_token.json silmeye gerek yok). Bkz. [[feedback_csrf-cache-poison-self-heal-fixed]]
- **push-failure stale lock** → upload-failure'da unlock etmiyordu → persistent session stale lock; fix failure'da unlock. Bkz. [[feedback_push-failure-stale-lock-persistent-session]]
- **create_cds_view XML-escape** → source escape değildi; fix html.escape; read-only=`as select from`; opaque hatada ham response.text yakala. Bkz. [[feedback_create-cds-view-xml-escape]]
- **MCP stdio subprocess deadlock** → adt_push 5-6 dk donuyordu; reviewer subprocess stdin=DEVNULL almayınca stdio pipe miras alıyordu; fix stdin=DEVNULL + timeout 30s. Bkz. [[feedback_mcp-stdio-subprocess-deadlock]]
- **adt_table_read pozisyonel hizalama** → ham positional data.data yanlış-hizalama yapıyordu; YAPISAL fix 2026-06-23 (3823b4b1) `data.pop('data')` → yalnız rows_labeled+columns döner. Alan-değeri rows_labeled'dan oku. Bkz. [[feedback_adt-table-read-pozisyonel-hizalama-tuzagi]]
