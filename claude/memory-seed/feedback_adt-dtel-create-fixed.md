---
name: feedback_adt-dtel-create-fixed
description: "MCP adt_dtel_create / create_dataelement domain-binding bug'ı KÖK-FİX edildi (2026-06-14) — /mcp restart sonrası tool güvenilir"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 791c30b9-6728-4e20-94d7-8d4a14484d2d
---

`sap_adt_lib.py::create_dataelement` (MCP `adt_dtel_create`'in arkasındaki) domain-binding bug'ı **2026-06-14 düzeltildi**.

**Kök sebep:** payload eski `dtel:wbobj` namespace (`http://www.sap.com/wbobj/dictionary/dtel`) + eksik adtcore attr (responsible/abapLanguageVersion/language) + yanlış `dtel:dataType` wrapper kullanıyordu → SAP parser typeName/labels'ı yok sayıyor → 201 ama activate "No domain or data type was defined".

**Fix:** §26.2 ÇALIŞAN payload'una çevrildi — `blue:wbobj` kök + nested `dtel:dataElement` + tüm adtcore attr + yeni `_get_domain_typeinfo()` helper domain'den dataType/length/decimals çekiyor. Test (ZSD001_E_ZZTEST→ZSD001_D_SEVKNO) create+activate+typeName-bağlı+4-label-dolu+active PASS, sonra silindi.

**Why:** Önceki her DTEL'de manuel REST fallback'e düşülüyordu (yavaşlık + tekrar).

**How to apply:** **`/mcp` restart sonrası** `adt_dtel_create` doğrudan kullanılabilir — artık domain bağını ve 4 label'ı doğru yazıyor. Yine de create sonrası `adt_get` ile typeName + version=active doğrula (alışkanlık). Eğer restart YAPILMADIYSA tool hâlâ eski kodu çalıştırır → manuel REST fallback ([[feedback_create-bdef-script-broken-use-blues-recipe]] benzeri reçete playbook adt-domain-dtel §26.2). Playbook §26 satır 24 "FIXED" olarak güncellendi.
