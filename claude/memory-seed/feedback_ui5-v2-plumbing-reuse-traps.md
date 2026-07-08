---
name: feedback_ui5-v2-plumbing-reuse-traps
description: "Freestyle UI5+V2 — plumbing'i kanonik §K'dan reuse et (app-kopya değil); save=sıralı update, nav=to_X; runtime-verify; Booking patinaj dersleri"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 5b0903c5-8f3f-4ff6-a38a-02986d37fb2e
---

Booking UI'da diğer ekranlardan çok daha fazla amatör patinaj oldu çünkü çalışan kardeş deseninin **plumbing'i** (sip_se/ihr_se save=`oModel.update`) yerine sıfırdan, kırılgan desenle yazıldı → çözülmüş bug'lar geri geldi. Kanonik desen + tuzaklar artık `playbook/ui-freestyle-odata-v2.md` §K/§J'de, ADR 0017'de, G3 validator'da (`check_ui5_freestyle_traps.py`) kodlu.

**Why:** "Use ZSD001 template" denmesine rağmen kopya-temelli değil "iskelet+yama" inşa edildi; runtime hata yalnız kullanıcı test edince çıktı; ben (lider) "done/verified"i runtime-doğrulamadan kabul ettim + recon'u implementasyon sanıp doğrulamadım.

**How to apply:**
- **Plumbing = REUSE (sıfırdan icat etme), iş-içeriği = BESPOKE.** Reuse edilen mekanik (§K): save = SIRALI `oModel.update(merge)` (setProperty+submitChanges DEĞİL — programatik değer kaydetmez; eş-zamanlı update = BO kilit çakışması); V2 nav = `to_X` (CDS `_X` DEĞİL — sessiz kırılır); `setData` tam şekil (`sel`/`hasSel` düşürme); master-detail SingleSelectMaster+removeSelections; MERGE'de boş tarih = `null` (`""` → 400). Bespoke: entity/alan/layout/iş-gating/VH/label — hiçbir ekran kopya değil.
- **"done/verified" kanıtsız kabul etme:** UI = `check_ui5_freestyle_traps.py` PASS + runtime smoke (G1 playwright-cli; node--check/XML-well-formed YETMEZ). SAP = adt_get active readback. Recon ≠ implementasyon.
- **Kör-bug yasak:** opak hatada (Kaydedilemedi) önce gerçek HTTP hatasını al (F12 Network/body veya gateway replikte), sonra tek fix.
- Bkz. [[feedback_done-tam-kapsam-dogrula]] · [[feedback_freestyle-ui-preflight]] · [[feedback_grid-liste-standardi]] · [[feedback_numeric-input-no-type-number]]
