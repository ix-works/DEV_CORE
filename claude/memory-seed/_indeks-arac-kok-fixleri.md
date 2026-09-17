---
name: _indeks-arac-kok-fixleri
description: Araç kök-fix tarihçesi — regresyon sözlüğü (güncel kural DEĞİL)
metadata: 
  node_type: memory
  type: reference
---

# Araç kök-fix tarihçesi — tohum indeksi

> Bu 10 kayıt *"şu araç bug'ı bulundu ve KÖK-FİX edildi"* der (çoğu 2026-06). Güncel bir
> kural değil, **regresyon sözlüğüdür**: aynı semptom yeniden görünürse buraya bak — daha
> önce yaşanmış mı, kökü neydi, nasıl kapandı. ⚠ *"Düzeltildi"* o günün ölçümüdür; araç
> sürümü değiştiyse yeniden ölç.

**10 kayıt.**

- [Adt dtel create fixed](feedback_adt-dtel-create-fixed.md) — MCP adt_dtel_create / create_dataelement domain-binding bug'ı KÖK-FİX edildi (2026-06-14) — /mcp restart sonrası tool güvenilir
- [Adt get ddic read fixed](feedback_adt-get-ddic-read-fixed.md) — MCP adt_get XML-based DDIC (DTEL/DOMA/TABL/struct/ttyp) okuma bug'ı kök-fix edildi — canlı objeye exists:false dönüyordu
- [Adt get namespace encode trap](feedback_adt-get-namespace-encode-trap.md) — adt_get namespace'li obje adındaki slash'ları encode etmiyordu → yanlış 404; kök-fix edildi
- [Adt table read pozisyonel hizalama tuzagi](feedback_adt-table-read-pozisyonel-hizalama-tuzagi.md) — adt_table_read footgun YAPISAL ÇÖZÜLDÜ 2026-06-23 (pozisyonel data.data söküldü, yalnız rows_labeled döner); kolon-değer iddiasını rows_labeled'dan oku
- [Create bdef script broken use blues recipe](feedback_create-bdef-script-broken-use-blues-recipe.md) — create_behavior_definition.py 404'lüyor — bozuk; BDEF create için proven blues.v1 reçetesini (create_rap_service.py) kullan
- [Create cds view xml escape](feedback_create-cds-view-xml-escape.md) — Yeni CDS yaratırken create_cds_view source'u XML'e escape etmeden gömüyordu → <>/</& 'Unknown error'; fix html.escape; ayrıca read-only consumption=select from (projection değil)
- [Csrf cache poison self heal fixed](feedback_csrf-cache-poison-self-heal-fixed.md) — CSRF cache-poison patinajı (3x 403 → fail) KÖK-FİX edildi 2026-06-14 — artık otomatik self-heal, elle .csrf_token.json silmek gerekmez
- [Mcp stdio subprocess deadlock](feedback_mcp-stdio-subprocess-deadlock.md) — sap-adt MCP push'u 5-6 dk sürüyordu: stdio MCP server'da subprocess.run stdin vermeyince çocuk parent'ın stdin pipe'ını miras alıp 120s donuyor; fix stdin=DEVNULL
- [Push failure stale lock persistent session](feedback_push-failure-stale-lock-persistent-session.md) — push_object FAILURE'da unlock etmiyordu → MCP persistent session stale lock'u tutuyor, sonraki push'lar aynı handle'ı reuse edip patinaj yapıyor
- [Source drift name collision fixed](feedback_source-drift-name-collision-fixed.md) — Drift-guard (ADR 0016) aynı-adlı farklı-tip dosyada sahte drift veriyordu — object_type filtresi eklendi (kök-fix)

<!-- makine-okunur erişilebilirlik çapası (C-MEM-01): indeks bütünlüğü kapısı
     cift-koseli-parantez linki arar, markdown link saymaz. Liste yukarıdakiyle AYNI olmalı. -->
[[feedback_adt-dtel-create-fixed]] · [[feedback_adt-get-ddic-read-fixed]] · [[feedback_adt-get-namespace-encode-trap]] · [[feedback_adt-table-read-pozisyonel-hizalama-tuzagi]] · [[feedback_create-bdef-script-broken-use-blues-recipe]] · [[feedback_create-cds-view-xml-escape]] · [[feedback_csrf-cache-poison-self-heal-fixed]] · [[feedback_mcp-stdio-subprocess-deadlock]] · [[feedback_push-failure-stale-lock-persistent-session]] · [[feedback_source-drift-name-collision-fixed]]
