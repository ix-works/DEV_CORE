---
name: feedback_adt-get-ddic-read-fixed
description: "MCP adt_get XML-based DDIC (DTEL/DOMA/TABL/struct/ttyp) okuma bug'ı kök-fix edildi — canlı objeye exists:false dönüyordu"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 612f1395-101e-440c-93a8-f64bda823d69
---

MCP `adt_get`, XML-based DDIC objelerini (dataelement/domain/table/structure/tabletype) `download_object`'a yönlendiriyordu → URL'e `/source/main` ekleniyordu (örn. `/ddic/dataelements/<ad>/source/main`) → DTEL/DOMA/TABL'da o endpoint YOK → 404 → CANLI objeye `exists:false` (recon'ları kör ediyordu: railway_node + partner DTEL domain tipleri okunamıyordu).

**Kök-fix (2026-06-16, `mcp_servers/sap_adt/tools/atom.py`):** `adt_get` artık XML-based DDIC tiplerini `client.get_ddic_object()`'a yönlendiriyor (doğru DDIC vendor Accept header + base URL, source/main YOK). Helper `_ddic_xml_type` + set `_DDIC_XML_TYPES`. Source-based objeler (class/program/CDS/bdef) değişmedi.

**Why:** Tooling kör-noktası deneme-yanılmaya ve "obje yok sanıp yeniden yaratma" riskine yol açıyordu (TAHMİN YASAK ihlali). DTEL domain tipi okunamayınca tablo-ALTER onay gate'i + assoc değişiklikleri eksik veriyle ilerliyordu.

**How to apply:** `/mcp restart` sonrası `adt_get <DTEL> dtel` artık `exists:true` + XML döner (canlı doğrulandı: ZSD001_E_RAILN → typeName KNOTN, CHAR10). Restart ÖNCESİ workaround = `python scripts/download_object.py --name X --type dataelement|domain|table --no-save` (zaten `get_ddic_object` kullanır). Namespace-encode fix'i ([[feedback_adt-get-namespace-encode-trap]]) ve DTEL-create fix'i ([[feedback_adt-dtel-create-fixed]]) ayrı bug'lardı; bu OKUMA yolu fix'i. Araç fix'i = lider işi ([[feedback_arac-kod-fix-lider-isi]]).
