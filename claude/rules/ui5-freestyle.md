---
globs: **/webapp/**/*.js, **/webapp/**/*.xml, **/webapp/**/*.properties, **/manifest.json, **/*.view.xml, **/*.controller.js
---

# Freestyle UI5 + OData V2 (L1b — bu kural eşleşen dosya okununca yüklenir)

## 0. PRE-FLIGHT ZORUNLU
Yazmadan önce oku: `core/playbook/ui-freestyle-odata-v2.md` §0 + `core/playbook/ui-backend-rap.md` §0.
Gate: `check_ui5_freestyle_traps.py`.

## 1. LİSTE = GRID (ADR 0008)
Liste/rapor ekranı **`sap.ui.table.Table`** (`sap.m.Table` değil). Native sort/filter menüsü +
DB varyant + kolon göster/gizle + Excel. Kanonik şablonu KOPYALA, sıfırdan yazma.
Gate: `check_list_view_grid.py`.

## 2. FİLTRE DESENİ (FE-32)
Select-options + `Contains`. `MultiInput` + value-help dialog. **`caseSensitive:false` YASAK.**
Gate: `check_filter_search_pattern.py`.

## 3. SIK TUZAKLAR
- **Sayısal input:** `type="Number"` KULLANMA → `type="Text"` + `onNumericLiveChange`.
- **Merge-key padding:** `"10"` vs `"000010"` sessizce null üretir → `parseInt` ile normalize et.
- **i18n:** etiket **HER İKİ** dosyada (`i18n.properties` + `i18n_tr.properties`); `i18n_tr` override eder.
- **Decimal:** ABAP decimal'i OData gövdesine `WRITE ... TO` ile yazma (locale bozar).
  Gate: `check_decimal_write_to.py`.

## 4. LOKAL ÇALIŞTIRMA
App dizininde `npm install` **YASAK** → paketin `ui/` workspace'inden `npm run start-noflp`.
`FIORI_TOOLS_*` `.conn_adt`'den okunur. Israrlı logon popup + `lrep 401` → **hesap kilidi** (SU01).

## 5. DEPLOY
Kanonik: `core/scripts/deploy_ui.py` (build + deploy + canlı hash). Yalın `fiori deploy` bayat
`dist/` gönderir → guard bloklar. **Lokal test onayı olmadan deploy YOK.**

📖 Derin referans: `core/standards/03-coding-ui-fiori.md` · `core/playbook/ui-freestyle-odata-v2.md`
