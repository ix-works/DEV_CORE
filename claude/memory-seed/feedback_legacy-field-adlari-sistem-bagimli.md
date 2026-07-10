---
name: feedback_legacy-field-adlari-sistem-bagimli
description: "<LEGACY_SOURCE> eski source'tan kopya yaparken standart SAP tablo alan adlarını yeni sistemde mutlaka teyit et — versiyon/eklenti farkı olabilir"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7091c15c-424a-42a9-bcf8-7c3f51f36d33
---

Eski sistem <LEGACY_SOURCE> SEVKEMRI/sources/cds/*.cds'lerinden yeni sisteme kopyalarken **standart SAP tablo field adları farklı olabilir**. Kapalı body copy + namespace rename yetmez; sistem versiyonu, enhancement category, eklenti seti, hatta lokalizasyon paketi alan adlarını değiştirir.

**Vaka 2026-05-14** — `ZSD001_DDL_SHIPPING_TYPES` CDS'i:
- <LEGACY_SOURCE> source'ta: `ShippingType.vsartkat as TransportCategory`
- Yeni sistemde aktivasyon hatası: "The column vsartkat is unknown"
- T173 source kontrol edildi: gerçek field **`vktra`** ("Mode of Transport")
- Eski sistemde belki vsartkat bir append-struct alanıydı veya farklı T173 versiyonu vardı
- Düzeltme: `vsartkat` → `vktra`

**Yapılması GEREKEN sıralı kontrol:**
1. Eski <LEGACY_SOURCE> source'tan alan ad listesi çıkar
2. Standart tablolar (T173, T001, VBAK, vb.) için yeni sistemden field listesini al:
   ```
   GET /sap/bc/adt/ddic/tables/<table_name>/source/main
   ```
3. Field-by-field kontrol — eski adı yeni sistemde var mı?
4. Yoksa: anlam eşleşmesini kullanıcıya teyit ettir (örn. `vsartkat` = "Mode of Transport" → yeni'de `vktra`)
5. Sonra CDS'i yaz

**Sık karşılaşılan tablolar ve kontrol gereksinimi:**
- `T173` (Shipping Types) — yeni sistemde sadece VSART, VKTRA, VSGRP. Diğer field'lar (vsartkat gibi) ya append'le ya yok.
- `VBAK/VBAP` — enhancement category'e göre append'ler farklı
- `LIPS/LIKP` — proje append'leriyle field listesi değişir (<PROJECT_NAME>'da ZZ1_ORDER_ORDER_DLI, ZZ1_ORDER_ITEM_DLI gibi)

**Why:** Eski sistemden alan adı kopyalama silent failure değildir, aktivasyon "unknown column" hatası verir. Ama yine de zaman kaybı. 30 saniyelik field listesi kontrolü 5 dakikalık debugging'i engeller.

**How to apply:** <LEGACY_SOURCE>'dan CDS/struct/program kopyaladığında, ilk push öncesi `grep` ile tüm Z olmayan field referanslarını çıkar (örn. `\.\w+\s+as\s+` regex'iyle). Yeni sistemde her birini teyit et. Şüpheli olan minimum 1 tanesi için tablo source'unu GET et.

İlgili: [[feedback_playbook-once-oku]], [[feedback_zli-obje-text-tahmin-yasak]]
