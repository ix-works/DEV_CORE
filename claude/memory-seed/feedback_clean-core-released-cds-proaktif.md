---
name: feedback_clean-core-released-cds-proaktif
description: "CDS/RAP yazmadan ÖNCE released CDS tercih et (MARA değil I_Product); released-WARNING'i sessiz geçme"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d6295d2a-8529-437b-ad66-d0d6ec8aebe0
---

CDS/RAP'te standart tablo okuyacağın zaman, **kod yazmaya başlamadan ÖNCE** released CDS successor'ını hatırla/kontrol et: `from mara` değil `from I_Product`. Otoriter harita: `governance/reference/released_successors.json` (SAP resmi PCE JSON'dan; MARA→I_Product+4, VBAP→I_SalesDocumentItem, LIPS→I_DeliveryDocumentItem...). `check_released_objects.py` reviewer'da WARNING verir ama **WARNING geçiştirilebilir** → ATC no-suppress disiplini gibi davran: ya released'a çevir, ya da bilinçli tablo kullanıyorsan **gerekçeni kullanıcıya bildir**. Sessiz pass YOK.

**Why:** Post-write WARNING reaktif; davranışı değiştirmesi için kuralı yazımdan ÖNCE içselleştirmem gerek. Clean Core Level A tercihi (ADR 0005-B READ'i yasaklamaz ama released CDS yeğlenir). Kullanıcı: "warning verdiğin için geçebilir ve yine MARA kullanmaya devam edebilirsin; en azından farkında olmalısın, hatta yazmadan önce hatırlamalısın."

**How to apply:** CDS/RAP işine başlarken `released_successors.json`'a bak (skill TETİKLEMELİ YÜKLEME CDS/RAP satırı + checklist C-CDS-FROM-04 / C-RAP-REL-01 hatırlatır). Tüm-tip released-API (class/FM) için SAP yerel ATC "Usage of APIs" otoriter. Dil-versiyonu/no-classic Clean Core aileleri bize uygulanmaz (dual-track on-prem). Bkz. [[feedback_atc-priority-1-zorunlu]] (aynı sessiz-pass disiplini).

**KULLANICI "MARM/std tablo kullan" DESE BİLE released successor varsa ONU kullan (2026-06-12, ZSD001 PAK):** Kullanıcı tüm alternatif CDS'leri bilemeyebilir; "MARM kullan" demesi **veriyi** kasteder, released eşdeğerini YASAKLAMAZ. Reviewer/`released_successors.json` bir successor öneriyorsa (MARM→I_ProductUnitsOfMeasure gibi) released'ı kullan. Kullanıcının sözü: "ben marm derim ama sistem zaten biliyor ve I_PRODUCTUNITSOFMEASURE kullan diyor; bu kullanmana engel olmamalı." Sadece released gerçekten işi yapamıyorsa (eksik alan vb.) std tabloya düş + gerekçeyi bildir. **Operasyonel tuzak:** released UoM çevrim alanları (I_ProductUnitsOfMeasure.QuantityNumerator=umrez / QuantityDenominator=umren) `@Semantics.quantity` (birim-referanslı) → aritmetik/CASE'te doğrudan kullanınca "Elements with required UNIT-reference are not supported" aktivasyon hatası; önce `cast( ... as abap.dec(n,m) )` ile birim semantiğini sıyır.
