sap.ui.define([
  "sap/ui/table/rowmodes/Auto",
  "sap/m/IllustratedMessage",
  "sap/m/Button"
], function (AutoRowMode, IllustratedMessage, Button) {
  "use strict";

  // ============================================================================================
  // SÜRÜM PARÇASI — UI5 >= 1.120 (ölçülen hedef: 1.120.52; bant gerekçesi: surum/1.120/README.md "Ne zaman"). Ortak gövde (app/) bu dosyayı ADIYLA çağırır;
  // sürüme bağlı API'ler YALNIZ burada yaşar. Kardeşi: surum/1.71/webapp/util/SurumParca.js (aynı imzalar).
  //  · satirModu  : rowMode aggregation + sap.ui.table.rowmodes.Auto (@since 1.119; visibleRowCountMode 1.119'da deprecated)
  //  · bosDurum   : noData = sap.m.IllustratedMessage (@since 1.98) + CTA Button (additionalContent)
  //  · bilesenArayuzleri : ["sap.ui.core.IAsyncContentCreation"] (@since 1.89; std/03 §4 zorunlu)
  //  · yapistirmaBagla : çok satırlı yapıştırma — MultiInput'un ÖZEL "_validateOnPaste" olayı (public API YOK;
  //    1.120.52 sap/m/MultiInput onpaste gövdesinde fireEvent("_validateOnPaste", {texts}, true) ölçüldü)
  //  · siraliMi   : kolon sıralı mı — sortOrder !== "None" (1.120.52 Column: sortOrder varsayılan "None",
  //                 "sorted" özelliği 1.120'de deprecated)
  //  · dogrulayiciMetni : MultiInput validator'ına gelen metin KAÇIŞLIDIR (1.120.52 _validateCurrentText →
  //                 addValidateToken({text: ManagedObject.escapeSettingsValue(sValue)})) ⇒ kaçış geri alınır.
  //                 Ters işlem: BindingParser.complexParser.escape = replace(/([\\\{\}])/g, "\\$1").
  // ============================================================================================

  var KACIS = /\\([\\{}])/g;

  // Excel'den yapıştırma satır/sekme ayırıcısı — MultiInput onpaste'in kendi ayırıcısıyla aynı.
  var PASTE_SPLIT = /\r\n|\r|\n|\t/g;

  function cokSatir(oEvent) {
    var oClip = oEvent && oEvent.originalEvent && oEvent.originalEvent.clipboardData, s;
    if (!oClip) { return false; }
    s = oClip.getData("text/plain") || "";
    if (s.length && s.endsWith("\r\n")) { s = s.substring(0, s.lastIndexOf("\r\n")); }
    return s.split(PASTE_SPLIT).length > 1;
  }

  return {
    surum: "1.120",

    // Component metadata.interfaces — IAsyncContentCreation @since 1.89 (std/03 §4 zorunlu).
    bilesenArayuzleri: ["sap.ui.core.IAsyncContentCreation"],

    satirModu: function (oTable, iMin) {
      oTable.setRowMode(new AutoRowMode({ minRowCount: iMin }));
    },

    // m: { title, description, ctaText, onCta }
    bosDurum: function (oTable, m) {
      oTable.setNoData(new IllustratedMessage({
        illustrationType: "sapIllus-NoSearchResults",
        title: m.title,
        description: m.description,
        additionalContent: [new Button({ text: m.ctaText, press: m.onCta })]
      }));
    },

    // Kolonun kullanıcı tarafından sıralanmış olup olmadığı (rebind'de sorter'ı yeniden kurmak için).
    siraliMi: function (oCol) {
      return oCol.getSortOrder() !== "None";
    },

    // Validator'ın aldığı metni HAM biçime getirir (ortak gövde token'ı setter'la kurar, kaçış istemez).
    dogrulayiciMetni: function (sText) {
      return String(sText === null || sText === undefined ? "" : sText).replace(KACIS, "$1");
    },

    // fnSatir(sSatir, aBad): satır başına çağrılır (token kurma + ekleme çağıranın işi) · fnBitti(aBad): tek toplu rapor.
    // Standart davranış (geçersiz satırı sessizce düşürme) preventDefault ile KAPATILIR; tarayıcının ham çok satırlı
    // metni alana yazması da onpaste delegesiyle engellenir.
    yapistirmaBagla: function (oMI, fnSatir, fnBitti) {
      oMI.attachEvent("_validateOnPaste", function (oEv) {
        var aBad = [];
        oEv.preventDefault();
        (oEv.getParameter("texts") || []).forEach(function (sLine) {
          var s = String(sLine === null || sLine === undefined ? "" : sLine).trim();
          if (s) { fnSatir(s, aBad); }
        });
        fnBitti(aBad);
      });
      oMI.addEventDelegate({ onpaste: function (oEv) { if (cokSatir(oEv)) { oEv.preventDefault(); } } });
    }
  };
});
