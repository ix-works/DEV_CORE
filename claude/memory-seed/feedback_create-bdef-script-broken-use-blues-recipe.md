---
name: feedback_create-bdef-script-broken-use-blues-recipe
description: "create_behavior_definition.py 404'lüyor — bozuk; BDEF create için proven blues.v1 reçetesini (create_rap_service.py) kullan"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 791c30b9-6728-4e20-94d7-8d4a14484d2d
---

**FIXED 2026-06-14** — `sap_adt_lib.py::create_behavior_definition` artık çalışıyor (throwaway test PASS). Eskiden BDEF create'te **404** dönüyordu: (1) yanlış content-type `application/vnd.sap.adt.behaviorDefinition+xml` (doğrusu `application/vnd.sap.adt.blues.v1+xml`), (2) yanlış endpoint `/sap/bc/adt/behaviordefinitions` (doğrusu `/sap/bc/adt/bo/behaviordefinitions`), (3) bozuk kapanış tag'i `<\bdef:...>`. Fonksiyon §32.6c blues reçetesine çevrildi + shell POST/source PUT `_request_with_csrf_retry` üzerinden. **MCP tool path'i için `/mcp` restart gerekir.**

**Why:** BDEF, blue/blueSource ailesinden (adtcore:type="BDEF/BDO"), SRVD ile aynı 2-step (shell + LOCK/PUT source/main + UNLOCK). Script bunu hiç yansıtmamış.

**How to apply:** Yeni BDEF yaratırken `create_behavior_definition.py` KULLANMA. Proven primitive'ler `scripts/create_rap_service.py` içinde: `bdef_shell_xml()` (blue:blueSource + BDEF/BDO + masterLanguage TR), endpoint `/sap/bc/adt/bo/behaviordefinitions`, CT `application/vnd.sap.adt.blues.v1+xml`, sonra LOCK→PUT source/main (text/plain)→UNLOCK. Aktivasyon: BDEF + behavior class BİRLİKTE (`/sap/bc/adt/activation`, body iki `objectReference`). Reçete: [[project_zsd011-rap-fittings]] adt-rap §32.6c. ZSD001_I_SIPSE coexistence spike (2026-06-14) ile kanıtlandı. T1: kalıcı düzeltme = create_behavior_definition.py'yi blues reçetesine güncelle (veya deprecate et). Aktivasyon yanıtında çakışmayı `type="E"`/`type="A"` + `activationExecuted` ile değerlendir — `severity=` attribute'u YOK (yanıltıcı false-PASS).
