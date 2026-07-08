---
name: feedback_push-failure-stale-lock-persistent-session
description: "push_object FAILURE'da unlock etmiyordu → MCP persistent session stale lock'u tutuyor, sonraki push'lar aynı handle'ı reuse edip patinaj yapıyor"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7a28f63f-6ff0-4fe7-88d3-e6cc7c9c76c5
---

`scripts/sap_client.py::push_object` source-upload BAŞARISIZ olunca lock'u **unlock ETMİYORDU** (except sadece `raise`; unlock yalnız BAŞARILI upload sonrası, aktivasyon-öncesi vardı). MCP server persistent stateful session kullandığından (SAPADTClient instance tool-çağrıları arası yaşar), başarısız push'tan kalan lock SAP tarafında takılı kalır → sonraki her `push_object` `lock_object()` çağrısı **AYNI stale handle'ı** geri alır (SAP session lock'u tutuyor) → tekrar eden başarısızlık + yanıltıcı hata.

**Why (KESİN, 2026-06-15 kanıtlı):** ZSD001 C4 push 5 tur boyunca aynı lock handle `F66BB933...` aldı, obje adt_lock_check'te NOT-locked görünmesine rağmen. Fix (push failure'da unlock) + `/mcp restart` (yeni session = stale lock düşer) sonrası **TAZE handle `AA736AA3...` geldi** → stale-lock bug'ı kesin doğrulandı + çözüldü. (NOT: o vakada 400 hatasının ASIL sebebi stale-lock DEĞİLDİ — ayrı eşzamanlı source-scan sorunuydu; ama stale-lock gerçek bir bug'dı ve her tekrar-push'ı kirletiyordu, teşhisi zorlaştırıyordu.)

**How to apply:** Fix uygulandı: `push_object` except bloğu push failure'da `unlock_object` çağırır (stale-lock guard). Tekrar-push patinajında **aynı lock handle dönüyorsa** (taze beklerken) → persistent session'da stale lock var; `/mcp restart` ile session sıfırla (lock düşer) + push_object'in failure-unlock'unun çalıştığını teyit et. Tooling fix = LİDER ([[feedback_arac-kod-fix-lider-isi]]); gateway raporlar, lider düzeltir. /mcp restart şart (in-memory session + kod). İlgili: [[feedback_csrf-cache-poison-self-heal-fixed]] (benzer cache-poison ama CSRF, bu LOCK).
