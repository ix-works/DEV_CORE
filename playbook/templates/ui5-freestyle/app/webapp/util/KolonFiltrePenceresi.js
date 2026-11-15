sap.ui.define([
  "sap/m/Dialog",
  "sap/m/Button",
  "sap/m/Select",
  "sap/ui/core/Item",
  "sap/m/Input",
  "sap/m/DatePicker",
  "sap/m/MessageStrip",
  "sap/m/Label",
  "sap/ui/layout/form/Form",
  "sap/ui/layout/form/FormContainer",
  "sap/ui/layout/form/FormElement",
  "sap/ui/layout/form/ColumnLayout",
  "./ColumnFilterParser"
], function (Dialog, Button, Select, CoreItem, Input, DatePicker, MessageStrip, Label,
             Form, FormContainer, FormElement, ColumnLayout, ColumnFilterParser) {
  "use strict";

  // ============================================================================================
  // Kolon filtresi seçim penceresi (std/03 §10.0.1 "Kolon filtresi", bug-checklist FE-32 (e)).
  // Kolon menüsündeki "Filtre…" öğesinden açılır. Koşul açılır listeden seçilir (listeyi tür belirler: ColumnFilterParser.kosulListesi),
  // değer yazılır/seçilir; "Arasında" için ikinci değer alanı açılır. Kolon başına TEK koşul.
  // Pencere yalnız koşul düğümünü üretir ({op,tur,deger,deger2} — ColumnFilterParser.kosulDugumu); sorguyu/filtreyi KURMAZ:
  // çağıran `uygula(kosul, dugum)` ile alır ve kendi toFilter → süzgeç akışına verir.
  //
  // Saf arayüz bileşeni: uygulama ad alanından bağımsız (bağımlılık GÖRELİ: ./ColumnFilterParser), metinler `bundle` parametresiyle gelir
  // ⇒ aynen kopyalanabilir.
  //
  //   KolonFiltrePenceresi.ac({
  //     sahip:  oTable,                         // isteğe bağlı: addDependent (model/yaşam döngüsü)
  //     bundle: oResourceBundle,                // kfp.* + flt.numberInvalid/dateInvalid/timeInvalid anahtarları
  //     baslik: "Belge Tarihi",                 // kolon etiketi
  //     tur:    "string"|"numeric"|"date"|"time",
  //     mevcut: { op, v, v2 } | null,           // doluysa pencere dolu açılır; "Filtreyi Kaldır" yalnız bu durumda etkindir
  //     uygula: function (kosul, dugum) {},     // geçerli koşulla Uygula
  //     kaldir: function () {}                  // Filtreyi Kaldır
  //   });
  //
  // Geçersiz değerde pencere KAPANMAZ; ilgili alan Error durumuna geçer ve formun altında uyarı şeridi görünür (MessageStrip Form içeriği olamaz — IFormContent değil).
  // ============================================================================================

  var HATA_ANAHTAR = { sayi: "flt.numberInvalid", tarih: "flt.dateInvalid", zaman: "flt.timeInvalid" };

  function hataMetni(oB, oSonuc, sHam) {
    if (oSonuc.neden === "bos" || !HATA_ANAHTAR[oSonuc.neden]) { return oB.getText("kfp.err.empty"); }
    // fonksiyonlu replace: girilen metindeki "$&" / "$1" özel değiştirme deseni sayılmasın.
    return oB.getText(HATA_ANAHTAR[oSonuc.neden]).replace("{0}", function () { return sHam; });
  }

  // Değer alanı: tarih → DatePicker (görüntü GG.AA.YYYY, değer yyyy-MM-dd) · diğerleri → Input type=Text (std/03 §17: type=Number YASAK).
  // Sayı alanında TR yazımı geçerlidir (ondalık virgül, binlik nokta): yalnız rakam . , + - boşluk dışı karakterler atılır
  // (std/03 §17 örneğindeki "," → "." dönüşümü UYGULANMAZ — Sayi.metindenSayi oturum dilinin biçimini ayrıştırır).
  function degerAlani(sTur, fnDegisti, fnGonder) {
    if (sTur === "date") {
      return new DatePicker({
        width: "100%", displayFormat: "dd.MM.yyyy", valueFormat: "yyyy-MM-dd",
        change: fnDegisti
      });
    }
    return new Input({
      width: "100%", type: "Text",
      liveChange: function (oEv) {
        var oSrc = oEv.getSource(), s = oEv.getParameter("value") || "", sSon = s;
        if (sTur === "numeric") { sSon = s.replace(/[^0-9.,+\-−\s]/g, ""); }
        // "value" özelliği yazım sırasında DOM'la eşitlenmez (change olayı bekler); hata durumu temizlenince alan yeniden çizilir ve
        // DOM, bayat özellik değerine döner ⇒ hatadan sonraki ilk tuş vuruşu silinir (ölçüldü). Bu yüzden önce özellik eşitlenir.
        if (sSon !== s) { oSrc.setValue(sSon); } else { oSrc.setProperty("value", sSon, true); }
        fnDegisti();
      },
      submit: fnGonder
    });
  }

  function uyariSeridi() {
    var oS = new MessageStrip({ type: "Error", showIcon: false, enableFormattedText: false, visible: false });
    oS.addStyleClass("sapUiSmallMarginBeginEnd sapUiTinyMarginBottom");
    return oS;
  }

  function ac(o) {
    var oB = o.bundle, sTur = o.tur, oMevcut = o.mevcut || null;
    var aOp = ColumnFilterParser.kosulListesi(sTur);
    var sOp0 = (oMevcut && aOp.indexOf(oMevcut.op) >= 0) ? oMevcut.op : aOp[0];
    var oDlg;

    var oSecim = new Select({
      width: "100%", autoAdjustWidth: false, selectedKey: sOp0,
      items: aOp.map(function (sOp) { return new CoreItem({ key: sOp, text: oB.getText("kfp.op." + sOp) }); }),
      change: function () { guncelle(); hataTemizle(); }
    });
    var oDeger1 = degerAlani(sTur, hataTemizle, uygula);
    var oDeger2 = degerAlani(sTur, hataTemizle, uygula);
    var oUyari = uyariSeridi();                 // Form içeriği olamaz (IFormContent değil) → Form'un altında, Dialog içeriğinde

    function sablon(oEtiket, oAlan) { return new FormElement({ label: oEtiket, fields: [oAlan] }); }
    var oSatirSecim = sablon(new Label({ text: oB.getText("kfp.condition"), labelFor: oSecim.getId() }), oSecim);
    var oSatirDeger1 = sablon(new Label({ text: oB.getText("kfp.value"), labelFor: oDeger1.getId() }), oDeger1);
    var oSatirDeger2 = sablon(new Label({ text: oB.getText("kfp.valueTo"), labelFor: oDeger2.getId() }), oDeger2);

    function guncelle() {                       // "Arasında" seçiliyken ikinci değer alanı görünür
      var bBt = (oSecim.getSelectedKey() === "BT");
      oSatirDeger2.setVisible(bBt);
      if (!bBt && oDeger2.getValueState() === "Error") { hataTemizle(); }
    }
    function hataTemizle() {
      [oDeger1, oDeger2].forEach(function (oAlan) {
        if (oAlan.getValueState() !== "None") { oAlan.setValueState("None"); oAlan.setValueStateText(""); }
      });
      oUyari.setVisible(false);
    }
    function hataGoster(oAlan, sMetin) {
      oAlan.setValueState("Error");
      oAlan.setValueStateText(sMetin);
      oUyari.setText(sMetin);
      oUyari.setVisible(true);
      oAlan.focus();
    }

    function uygula() {
      var sOp = oSecim.getSelectedKey(), bBt = (sOp === "BT");
      var s1 = oDeger1.getValue() || "", s2 = bBt ? (oDeger2.getValue() || "") : "";
      hataTemizle();
      var oSonuc = ColumnFilterParser.kosulDugumu(sOp, s1, s2, sTur);
      if (!oSonuc.ok) {
        if (oSonuc.alan === 2) { hataGoster(oDeger2, hataMetni(oB, oSonuc, s2)); }
        else { hataGoster(oDeger1, hataMetni(oB, oSonuc, s1)); }
        return;                                 // pencere kapanmaz
      }
      oDlg.close();
      o.uygula(oSonuc.kosul, oSonuc.dugum);
    }

    var oForm = new Form({
      editable: true,
      layout: new ColumnLayout({ columnsM: 1, columnsL: 1, columnsXL: 1 }),
      formContainers: [ new FormContainer({
        formElements: [oSatirSecim, oSatirDeger1, oSatirDeger2]
      }) ]
    });

    // Dolu açılış: koşul + değer(ler). Tarihte değer "yyyy-MM-dd" (valueFormat) olarak saklanır.
    if (oMevcut) {
      oDeger1.setValue(oMevcut.v || "");
      oDeger2.setValue(oMevcut.v2 || "");
    }
    guncelle();

    oDlg = new Dialog({
      title: oB.getText("kfp.title", [o.baslik]),
      contentWidth: "28rem",
      draggable: true,
      initialFocus: oDeger1,
      content: [oForm, oUyari],
      buttons: [
        new Button({ text: oB.getText("kfp.apply"), type: "Emphasized", press: uygula }),
        new Button({
          text: oB.getText("kfp.remove"), enabled: !!oMevcut,
          press: function () { oDlg.close(); o.kaldir(); }
        }),
        new Button({ text: oB.getText("kfp.cancel"), press: function () { oDlg.close(); } })
      ],
      afterClose: function () { oDlg.destroy(); }
    });
    if (o.sahip) { o.sahip.addDependent(oDlg); }
    oDlg.open();
    return oDlg;
  }

  return { ac: ac };
});
