---
name: feedback_adt-get-namespace-encode-trap
description: "adt_get namespace'li obje adındaki slash'ları encode etmiyordu → yanlış 404; kök-fix edildi"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 4cc5b852-1de0-4cd4-aa55-3ab42f32a9fc
---

`adt_get` (ve `download_object`/`get_object_metadata`) namespace'li obje adlarında (`/SCWM/DE_HUIDENT` gibi) slash'ları URL-encode ETMİYORDU → path bozuluyor (`.../dataelements//scwm/de_huident`) → **yanlış 404 (yok sanılıyor)**. Gerçek-yokluk DEĞİL, encoding bug'ı.

**Why:** 2026-06-15 ZSD001 depo-birim DTEL'i ararken `/SCWM/DE_HUIDENT` "yok (404)" denildi → kullanıcının istediği DTEL'i neredeyse "mevcut değil" diye reddedecektik. `adt_search_objects` doğru encode ediyordu (`%2fscwm%2f...`) ve buldu → çelişki yakalandı.

**How to apply:** Kök-fix `scripts/object_types.py::get_object_url` → `quote(object_name.lower(), safe='')` (slash→%2f; normal adlar değişmez). **`/mcp restart` gerekir** (MCP süreci object_types'ı import ediyor). Namespace'li (`/SCWM/`, `/SCDL/`...) standart objelerde `adt_get` 404 dönerse: bu fix yüklü mü + restart yapıldı mı bak; `adt_search_objects` ile çapraz-doğrula (o her zaman doğru encode eder). Genel ders: typed-tool 404'ü "kesin yok" sanma; ikinci yöntemle teyit (bkz. [[feedback_done-tam-kapsam-dogrula]] · [[feedback_arac-kod-fix-lider-isi]]).
