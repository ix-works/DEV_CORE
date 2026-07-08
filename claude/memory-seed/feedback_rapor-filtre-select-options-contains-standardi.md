---
name: feedback_rapor-filtre-select-options-contains-standardi
description: Rapor/liste filtre ekranı = select-options (MultiInput) + harf-duyarsız Contains varsayılan; caseSensitive:false YASAK (/IWBEP toupper/tolower 400)
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 968d8d8f-00ae-498a-9770-6e066dc35c46
---

Rapor/liste **filtre + value-help + grid sütun-başlığı araması** için PROJE STANDARDI (kullanıcı kararı 2026-06-24, "ben söylemeden default olmalı"). Gate: `check_filter_search_pattern.py` (FE-32, run_all'a WIRED, HARD). Standart: `standards/03-coding-ui-fiori.md` §10.0.1 · teknik: `playbook/ui-freestyle-odata-v2.md` §C5 · checklist FE-32.

**Why:** Rapor filtreleri pivot/analiz kaynağı → çoklu-değer + aralık (ABAP SELECT-OPTIONS pariteli) şart. Ayrıca harf-duyarsız "içeren" arama (kullanıcı `gül` yazınca `GÜLAK MAKİNA…` bulmalı) varsayılan olmalı — istemese de.

**How to apply:**
- Filtre alanı = `sap.m.MultiInput` + `sap.ui.comp.valuehelpdialog.ValueHelpDialog` (değer-tablosu + ranges sekmesi); tek-değer `<Input>` DEĞİL. Tarih=DateRangeSelection, durum=SegmentedButton istisna. manifest libs'e `sap.ui.comp`.
- **⛔ `caseSensitive:false` ASLA kullanma** → UI5 V2 `$filter`'a `toupper()`/`tolower()` enjekte eder; SAP Gateway /IWBEP bu fonksiyonları DESTEKLEMEZ → **HTTP 400** "Function toupper/tolower is not supported" (SAP Note 1797736) → arama hiç sonuç döndürmez (canlı kanıt 2026-06-24, GÜLAK vakası). `new Filter(path, FilterOperator.Contains, q)` (caseSensitive parametresi VERME) → düz `substringof` zaten harf-duyarsız (DB collation; `gül`→`GÜLAK` 200).
- Wildcard ortak `_parseSearchTerm`: `*x*`/`x`→Contains · `x*`→StartsWith · `*x`→EndsWith (startswith/endswith /IWBEP'te DESTEKLENİR — toupper'ın aksine; canlı probe). Literal asterisk aranmaz.
- Kod/serbest-metin alanı düz-token default `Contains` (`defaultOp`); grid sütun filtresi `TablePersonalizer._onColumnFilter` (preventDefault + string=düz Contains).
- **Kanonik referans (kopyala): `ERP/SD/ZSD001_CLC/ui/sales_order_report/`.**
- Bağlı: [[feedback_grid-liste-standardi]] · [[feedback_liste-ekrani-alv-standardi]] · [[feedback_freestyle-ui-preflight]] · [[feedback_kural-gate-lenmeli-yoksa-anlamsiz]]
