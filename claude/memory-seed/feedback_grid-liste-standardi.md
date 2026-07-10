---
name: feedback_grid-liste-standardi
description: ALV-tarzı liste/rapor ekranları artık sap.ui.table.Table (grid) standardı; salt-okunur RAP rapor reçetesi (wrapper+DCL+SRVD/SRVB)
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9032e66e-45f9-47c0-af9b-23b771ffe0a7
---

ALV-tarzı liste/rapor ekranları **`sap.ui.table.Table` (grid)** ile yapılır (kullanıcı kuralı, 2026-06-08). m.Table (responsive) sadece mobil-öncelikli/hücre-zengin ekran istisnası.

**Why:** Grid ALV davranışını verir — yatay scroll + sanal scroll (binlerce satır) + kolon resize/reorder/freeze + native sort/filter. m.Table'da yatay scroll yok, growing hepsini DOM'a alır. Kullanıcı klasik ALV deneyimini istiyor. Pilot ZSD001 → onaylandı → tüm rapor app'leri grid'e çevrildi (ZSD001/005/006 + voyage + container_report).

**How to apply (UI):** Yeni liste/rapor = kanonik şablon app'i KOPYALA (`ERP/SD/ZSD001_CLC/ui/sales_order_report/` veya delivery_report) + kolon/filtre/servis değiştir. `sap.ui.table.Table`: visibleRowCountMode Auto, selectionMode None (liste)/Single (master-detail nav: Link/rowAction Navigation), enableColumnReordering+Freeze, threshold 200, rows binding, toolbar table:extension. Kolonlar: width tip-bazlı (date 7/time 6/amount-qty 8 End/kısa 8/ad-uzun-concat 16/default 10) + sortProperty + filterProperty + Text wrapping=false. Sort/filter = grid NATIVE menü (m.Table'daki columnmenu.Menu+infoToolbar GEREKMEZ). TablePersonalizer grid sürümü = kolon göster/gizle + DB varyant/default (layout: visible+width+index, [[feedback_api-call-ic-gateway-proxy]] değil → ZSD000_UI_VARIANT_O2) + Excel. Tam reçete: playbook/ui-freestyle-odata-v2.md §E; standards/03 §10.0.

**Grid bir DİALOG/picker içindeyse (2026-06-12, ZSD001 Sipariş Ekle):** `sap.m.Dialog`'un kendi scroll container'ı `sap.ui.table` Auto-yükseklik hesabını bozar → grid yarıda kesilir. Fix: **Dialog'a `verticalScrolling="false" horizontalScrolling="false"`** → grid alanı tam doldurur, kendi scroll'unu yönetir. Picker JSONModel ile beslenir (OData değil): kolonlara `sortProperty`+`filterProperty` koymak yeter → başlık menüsünde sort/filtre client-side otomatik çalışır (ekstra kod yok). Editable hücre (Input) varsa `selectionBehavior="RowSelector"` → input'a tıklayınca satır seçilmez (seçim onay-kutusundan). Seçim API'si m.Table'dan FARKLI: `getSelectedItems()`→`getSelectedIndices()`+`getContextByIndex(i).getObject()`, `removeSelections(true)`→`clearSelection()`.

**Salt-okunur rapor RAP backend reçetesi (3× kanıt):** wrapper view entity `as select from <klasik DDL>` (key + @AccessControl #CHECK, klasiğe dokunma) → DCL (V_VBAK_VKO/VKORG/ACTVT='03') → SRVD (expose main + ortak ZSD000_I_*VH) → SRVB (OData V2) publish. BDEF/behavior YOK (salt-okunur). Tuzaklar: (1) **EXCRT/kur conversion-exit alanları → cast(.. as abap.dec(9,5))** yoksa OData publish ERROR "Do not use conversion exit"; (2) concat ("kod-tanım") alanlarda raw kod yok → F4 VH kod verir, filtre concat alanına StartsWith "kod-"; (3) populate_cds_views --force-recreate brand-new için; mevcut güncelleme lock+set_object_source helper. İlgili: [[project_zsd001-rap-reports]] · [[feedback_liste-ekrani-alv-standardi]] · [[feedback_freestyle-ui-preflight]]
