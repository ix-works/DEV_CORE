---
paths: **/webapp/**/*.js, **/webapp/**/*.xml, **/webapp/**/*.properties, **/manifest.json, **/*.view.xml, **/*.controller.js
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

## 6. UI BUILD DONE-CRITERIA + LİDER DOĞRULAMA (ADR 0017 — AGENTS §2'den taşındı, D1 2026-08-01)
1. **Plumbing'i icat etme — içeriği değil (app-kopyalama DEĞİL):** Freestyle UI5+V2'nin **mekanik/plumbing** kısmı (save=sıralı `update(merge)`, nav=`to_X`, `setData` tam şekil, master-detail seçim-wiring, MERGE tarih-null) **tek-doğru-yol, uygulamadan bağımsız** → [`playbook/ui-freestyle-odata-v2.md`](playbook/ui-freestyle-odata-v2.md) **§K**'yı **referans al, sıfırdan icat etme** (icat = çözülmüş bug'ı geri getirmek). **Uygulamaya özel her şey BESPOKE yazılır** (entity/servis, alan listesi, ekran layout/grid, iş/gating kuralları, VH hedefleri, label, akış) — hiçbir ekran diğerinin kopyası değildir. Sınır: *framework-plumbing = reuse · iş-içeriği = bespoke*.
2. **"done/verified" kanıtsız KABUL EDİLMEZ** (lider): UI build için → `check_ui5_freestyle_traps.py` PASS **+ runtime smoke** (G1 playwright-cli, yoksa elle console: zero render error + ana akış). SAP yazımı için → `adt_get` active readback. "node --check OK / XML well-formed" runtime/fonksiyonel hatayı YAKALAMAZ — yeterli değil.
3. **Recon ≠ implementasyon:** Bir recon dokümanı "done" değildir. Çıkarılan kural/gating UI'a **gerçekten kodlandı mı** lider doğrular. *Done = tam kapsam:* "tamam" demeden önce çıktı, işin TAM kapsamına karşı madde-madde doğrulanır; bilinçli ertelenen parça açıkça flag'lenir + register'a yazılır (sessiz eksik = done değil).
4. **Kör-bug YASAK:** "Kaydedilemedi" gibi opak hatada deneme-yanılma yapma → önce **gerçek hatayı** al (F12 Network/Console status+body, ya da gateway ile birebir replikte). Kanıtsız tek satır bile değiştirme.

---
