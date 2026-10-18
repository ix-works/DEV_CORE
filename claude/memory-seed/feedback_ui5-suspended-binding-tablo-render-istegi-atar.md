---
name: feedback_ui5-suspended-binding-tablo-render-istegi-atar
description: "sap.ui.table view'daki rows binding `suspended:true` olsa da render'da filtresiz OData isteği gitti (1.120, mock 3/3) — koşullu ilk istek için binding'i controller'da bindRows ile kur"
metadata:
  type: feedback
  seed: evet
---

Filtre sayfasından gelinmediğinde (doğrudan `#/route`, F5) liste HİÇ istek atmasın diye view'da `rows="{path:..., suspended:true}"` + `_onMatched`'te filtre yaz + `resume()` deseni **tutmadı**: `isSuspended()=true` iken tablo render'ında `getContexts()` filtresiz `$skip=0&$top=…&$inlinecount=allpages` isteği attı (bir projenin başlık listesi, UI5 1.120.23, mock, 3 temiz yüklemede 3/3). Ayrıca `filter()` suspend'i yok sayar (`ODataListBinding` `bIgnoreSuspend`).

**Çalışan desen:** view'da `rows` binding YOK; `_onMatched`: zorunlu filtre boşsa `getRouter().navTo("filter", {}, true)` + return; doluysa ilk seferde `oTable.bindRows({path, parameters:{countMode:"Inline"}, filters:this._buildFilters()})`, sonraki girişlerde mevcut binding'e `filter()`. TablePersonalizer/Excel/sayaç `getBinding("rows")` null kontrolü yapmalı.

**Why:** suspend yöntemi kâğıt üstünde doğru görünür; bug-gate bile ilk turda "doğru" dedi — ölçüm mock tarayıcıda yapılınca çöktü.
**How to apply:** "ilk istek gitmesin" iddiası her zaman Network'te ÖLÇÜLÜR; kaynak okuması yetmez.
Son-doğrulama: 2026-10-05 · Applies-to: freestyle UI5 1.120 + OData V2 + sap.ui.table
