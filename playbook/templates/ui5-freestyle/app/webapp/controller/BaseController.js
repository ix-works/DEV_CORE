sap.ui.define([
  "sap/ui/core/mvc/Controller",
  "sap/ui/core/UIComponent",
  "sap/ui/core/routing/History",
  "com/example/alan/uygulama/util/Tarih"
], function (Controller, UIComponent, History, Tarih) {
  "use strict";

  return Controller.extend("com.example.alan.uygulama.controller.BaseController", {
    getRouter: function () { return UIComponent.getRouterFor(this); },
    getModel: function (sName) { return this.getOwnerComponent().getModel(sName); },
    getResourceBundle: function () { return this.getOwnerComponent().getModel("i18n").getResourceBundle(); },
    i18n: function (sKey, aArgs) { return this.getResourceBundle().getText(sKey, aArgs); },
    navTo: function (sRoute, oParams, bReplace) { this.getRouter().navTo(sRoute, oParams, bReplace); },

    onNavBack: function () {
      if (History.getInstance().getPreviousHash() !== undefined) {
        window.history.go(-1);
      } else {
        this.getRouter().navTo("filter", {}, true);
      }
    },

    // Tarih-yalnız alan (Edm.DateTime + display-format=Date, arkada DATS) — bug-checklist FE-45. Tek kaynak
    // util/Tarih.js (gerekçe orada): DatePicker/DateRangeSelection YEREL gece yarısı verir, V2 UTC gönderir ⇒
    // seçilen takvim günü UTC gece yarısına taşınır; backend'den okunan (zaten UTC gece yarısı) değer korunur.
    // Şablonda tarih şu yollardan gider — hepsi util/Tarih'ten geçer: seçim ekranı tarih aralığı
    // (List._buildFilters) · grid kolon başlığı tarih filtresi (TablePersonalizer, Tarih.metindenGun) ·
    // değişiklik ekranı gövdesi (Change._pick). Yeni bir tarih yolu (function import parametresi vb.)
    // eklersen o da buradan geçer; ham metin ya da yerel gece yarısı gönderme.
    utcGun: function (d) {
      return Tarih.utcGun(d);
    },

    // OData hata gövdesinden GERÇEK SAP mesajı (playbook §B9 — sabit i18n metni yutmaz).
    parseError: function (oErr) {
      var s = "";
      var sBody = (oErr && (oErr.responseText || (oErr.response && oErr.response.body))) || "";
      try {
        var o = typeof sBody === "string" ? JSON.parse(sBody) : sBody;
        if (o && o.error) {
          s = (o.error.message && (o.error.message.value || o.error.message)) || "";
          if (!s && o.error.innererror) { s = o.error.innererror.message || ""; }
        }
      } catch (e) {
        // gövde XML/düz metin olabilir → aşağıdaki yedek
      }
      if (!s) {
        s = (oErr && (oErr.message || oErr.statusText)) || ("HTTP " + ((oErr && oErr.statusCode) || "?"));
      }
      return String(s);
    }
  });
});
