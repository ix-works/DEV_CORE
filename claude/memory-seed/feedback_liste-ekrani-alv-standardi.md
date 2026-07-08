---
name: liste-ekrani-alv-standardi
description: Her liste ekranı (TÜM <PROJECT_NAME> uygulamaları) ALV-paritesi standardını OTOMATİK içerir — kullanıcı istemese bile
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 08868cc7-ead9-4d38-b6fe-2fd1fd3eb04c
---

<PROJECT_NAME>'de yapılan **her** freestyle SAPUI5 uygulamasında **her liste
ekranı**, kullanıcı ayrıca istemese bile, ALV-paritesi standart bileşenini
**otomatik** içermeli (kullanıcı açık talimatı, 2026-05-19; ADR 0008).

> **⚠️ TABLO TEKNOLOJİSİ GÜNCEL (2026-06-08): GRID.** Bu dosya ALV-paritesinin
> **HER liste ekranında ZORUNLU** olduğu ÜST-İLKESİDİR (hâlâ geçerli). Ama
> aşağıdaki m.Table-spesifik mekanik (madde 1-2: `columnmenu.Menu` + `infoToolbar`)
> **artık kanonik DEĞİL** — liste/rapor ekranları `sap.ui.table.Table` (grid) ile
> yapılır; grid sort/filtre NATIVE menüden gelir (columnmenu.Menu+infoToolbar
> GEREKMEZ). Kanonik reçete + util grid-sürümü: [[feedback_grid-liste-standardi]]
> + standards/03 §10.0 + playbook/ui-freestyle-odata-v2.md §E. m.Table yalnız
> mobil-öncelikli/hücre-zengin istisna. Madde 3-5 (Kolonlar+Varyant+Excel) grid'de
> de geçerli (TablePersonalizer grid sürümü).

Bileşen (m.Table-LEGACY mekaniği — yalnız mobil-istisna; grid için yukarıdaki devre bak):
1. (m.Table-legacy) Kolon başlığı menüsü (`sap.m.table.columnmenu.Menu`) → grid'de
   NATIVE menü kullanılır, bu GEREKMEZ.
2. (m.Table-legacy) Aktif filtre çubuğu (infoToolbar) → grid'de native; GEREKMEZ.
3. **Kolonlar göster/gizle + VARYANT** (2026-06-08 geliştirildi; grid'de de geçerli): ortalanmış
   geniş `sap.m.Dialog` (30rem, draggable/resizable, SearchField, Tümünü
   Seç/Kaldır, scroll — kolon isimleri TAM görünür; eski dar popover isimleri
   kesiyordu). **Kolon-seçim varyantları** (ALV layout): Varyant Select +
   Farklı Kaydet/Sil, localStorage `<persoKey>_vars`, "(Standart)"=tümü;
   üzerine-yazma + silme `MessageBox.confirm` onaylı. Bu artık kanonik
   util'in parçası → **yeni raporlar kopyalayınca DEFAULT gelir** (kullanıcı teyidi).
4. Excel export (`sap.ui.export.Spreadsheet`): tüm filtreli satırlar,
   kapsam sorulu (Görünür/Tüm).
5. localStorage kalıcı; selection/scr1 filtresiyle AND.

**Why:** Kullanıcılar liste ekranlarını SAP ALV gibi kullanıyor;
tutarlılık + ORDER'de bu kanıtlandı. `P13nDialog`/`TablePersoController`
denendi, model-sync/persoKey kırılganlığı yüzünden REDDEDİLDİ.

**How to apply:** Yeni liste ekranı görevinde sormadan: GRID (`sap.ui.table.Table`)
kanonik şablon app'i kopyala ([[feedback_grid-liste-standardi]]), TablePersonalizer
(grid sürümü) + kolon meta (key/path/colId/text/type), "Kolonlar"/"Excel" buton +
i18n (`op.* flt.* exp.* btn.cols btn.excel`); sort/filtre grid NATIVE menüden
(columnmenu/infoToolbar GEREKMEZ). Standart: standards/03 §10.0 (grid);
pattern: playbook/ui-freestyle-odata-v2.md §E; checklist UI-PERSO-01. Bağlı:
[[feedback_freestyle-ui-preflight]] · [[project_sprint-plan-rap-revize]] (sprint şablonuna
da bu DoD girer).
