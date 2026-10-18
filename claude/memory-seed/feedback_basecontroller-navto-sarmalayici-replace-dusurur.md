---
name: feedback_basecontroller-navto-sarmalayici-replace-dusurur
description: "BaseController `navTo(sRoute, oParams)` sarmalayıcısı 3. argümanı (bReplace) DÜŞÜRÜR — guard yönlendirmesi push olur, tarayıcı geri tuşu döngüye girer; replace gerekiyorsa getRouter().navTo doğrudan"
metadata:
  type: feedback
  seed: evet
---

Şablon BaseController'larda yaygın sarmalayıcı `navTo: function (sRoute, oParams) { this.getRouter().navTo(sRoute, oParams); }` yalnız iki argüman iletir. `this.navTo("filter", {}, true)` yazınca `true` sessizce düşer, `Router.navTo` `setHash` (push) yapar. Guard senaryosunda (doğrudan `#/header` → filtre sayfasına yönlendir) geçmiş `[#/header, #/]` olur; geri tuşu `#/header`'ı açar, guard yine yönlendirir ⇒ **geri tuşuyla uygulamadan çıkılamaz**.

Çare: `this.getRouter().navTo("filter", {}, true)` ya da sarmalayıcıyı `navTo(sRoute, oParams, bReplace)` ile genişlet. Kod yorumu "replace=true" diyordu, davranış push'tu — bir projenin FE bug-gate'i yakaladı (2026-10-05, Router.js 1.120.23 kaynağıyla).

**How to apply:** replace/guard yönlendirmesi yazarken sarmalayıcının imzasını oku; argüman sayısı uyuşmazlığı hata vermez.
Son-doğrulama: 2026-10-05 · Applies-to: freestyle UI5 (sap.m.routing.Router)
