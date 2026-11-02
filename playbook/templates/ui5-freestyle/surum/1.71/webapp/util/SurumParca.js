sap.ui.define([
  "sap/m/VBox",
  "sap/m/Text",
  "sap/m/Button"
], function (VBox, Text, Button) {
  "use strict";

  // ============================================================================================
  // SÜRÜM PARÇASI — UI5 1.71 (ölçülen hedef: 1.71.85). Ortak gövde (app/) bu dosyayı ADIYLA çağırır;
  // sürüme bağlı API'ler YALNIZ burada yaşar. Kardeşi: surum/1.120/webapp/util/SurumParca.js (aynı imzalar).
  //  · satirModu  : visibleRowCountMode "Auto" + minAutoRowCount (1.71.85'te rowmodes/Auto modülü YOK — CDN 404;
  //                 rowMode aggregation var ama visibility "hidden")
  //  · bosDurum   : noData = VBox(Text + CTA Button) (sap.m.IllustratedMessage 1.71.85'te YOK — CDN 404;
  //                 Table.noData tipi sap.ui.core.Control, altTypes string — ölçüldü)
  //  · bilesenArayuzleri : [] (IAsyncContentCreation @since 1.89 — 1.71.85 sap/ui/core/library-dbg.js'te 0 eşleşme)
  //  · yapistirmaBagla : 1.120 kardeşiyle AYNI gövde — 1.71.85 sap/m/MultiInput onpaste'i de
  //                 fireEvent("_validateOnPaste", {texts}, true) çağırır (ölçüldü); public addValidateToken 1.71'de YOK.
  //  · siraliMi   : kolon sıralı mı — getSorted() (1.71.85 Column: sorted varsayılan false, sortOrder varsayılan
  //                 "Ascending"; SortOrder enum'unda "None" YOK ⇒ "None" karşılaştırması her kolonu sıralı sayar)
  //  · dogrulayiciMetni : MultiInput validator'ına gelen metin HAMDIR (1.71.85 _validateCurrentText →
  //                 _tokenizer._addValidateToken({text: text}), kaçış yok) ⇒ olduğu gibi döner.
  // ============================================================================================

  var PASTE_SPLIT = /\r\n|\r|\n|\t/g;

  function cokSatir(oEvent) {
    var oClip = oEvent && oEvent.originalEvent && oEvent.originalEvent.clipboardData, s;
    if (!oClip) { return false; }
    s = oClip.getData("text/plain") || "";
    if (s.length && s.endsWith("\r\n")) { s = s.substring(0, s.lastIndexOf("\r\n")); }
    return s.split(PASTE_SPLIT).length > 1;
  }

  return {
    surum: "1.71",

    // Component metadata.interfaces — sap.ui.core.IAsyncContentCreation @since 1.89, 1.71.85 core'da YOK ⇒ boş.
    // Async içerik manifest'teki rootView "async": true + routing "async": true ile sağlanır.
    bilesenArayuzleri: [],

    satirModu: function (oTable, iMin) {
      oTable.setVisibleRowCountMode("Auto");
      oTable.setMinAutoRowCount(iMin);
    },

    // m: { title, description, ctaText, onCta }
    bosDurum: function (oTable, m) {
      oTable.setNoData(new VBox({
        alignItems: "Center",
        justifyContent: "Center",
        items: [
          new Text({ text: m.title }).addStyleClass("sapUiTinyMarginBottom"),
          new Text({ text: m.description }).addStyleClass("sapUiSmallMarginBottom"),
          new Button({ text: m.ctaText, press: m.onCta })
        ]
      }).addStyleClass("sapUiMediumMargin"));
    },

    // Kolonun kullanıcı tarafından sıralanmış olup olmadığı (rebind'de sorter'ı yeniden kurmak için).
    siraliMi: function (oCol) {
      return oCol.getSorted();
    },

    // Validator'ın aldığı metni HAM biçime getirir (ortak gövde token'ı setter'la kurar, kaçış istemez).
    dogrulayiciMetni: function (sText) {
      return sText;
    },

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
