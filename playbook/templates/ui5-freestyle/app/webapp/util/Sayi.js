sap.ui.define([
  "sap/ui/core/format/NumberFormat"
], function (NumberFormat) {
  "use strict";

  // ============================================================================================
  // Sayısal alan (Edm.Decimal / Edm.Int* / Edm.Double) kolon filtresi yardımcısı.
  // V2 ODataModel filtre değerini $filter'a Edm tipine göre DİZGİ BİRLEŞTİRMESİYLE yazar: Decimal → v + "m",
  // Int64 → v + "l", Double → v + "d", Single → v + "f", Int32/Int16/Byte → String(v) (1.71.85
  // sap/ui/model/odata/ODataUtils-dbg.js:535-553 · 1.120.52 :559-577). Ham metin filtre değeri yapılırsa oturum
  // dilinin ayırıcıları OData'ya gider: TR "1.250" (bin iki yüz elli) → "1.250m" = 1,25 aranır, SESSİZ.
  // Bu yüzden metin oturum dilinin sayı biçimiyle ayrıştırılır ve OData'ya noktalı, gruplamasız, üssüz bir
  // dizgi ("1250", "-1250.5") verilir — bu biçim yukarıdaki tüm Edm dallarında geçerli bir literal üretir.
  //
  // NumberFormat.getFloatInstance({parseAsString:true}) (iki sürümde var; parseAsString @since 1.28.2) ayrıştırır.
  // Gruplama ayırıcısının YERİ 1.71.85'te denetlenmez (ayrıştırma deseni [0-9<grup>]+ — "1.25" TR'de 125 olur);
  // sıkı gruplama seçeneği (strictGroupingValidation) 1.71.85'te YOK (NumberFormat-dbg.js 0 eşleşme; 1.96.51'de var)
  // ⇒ gruplama, ayrıştırılan değerin AYNI biçimle yeniden yazılmış tam kısmıyla karşılaştırılarak doğrulanır.
  // Ayrıştırılamayan / gruplaması tutmayan / rakam-işaret-ayırıcı dışında karakter taşıyan metin → null.
  // SINIR: kolon meta'sı Int/Decimal ayırmaz — tamsayı kolonuna kesirli değer ("1,5") "1.5" olarak gider. Gateway'in
  // bunu reddedip grid hata kutusunun (List.controller _onRequestFailed) açılması BEKLENİR ama ÖLÇÜLMEDİ (backend yok).
  // ============================================================================================

  var oBicim = null, oAyirici = null;

  function bicim() {
    if (!oBicim) { oBicim = NumberFormat.getFloatInstance({ parseAsString: true }); }
    return oBicim;
  }

  // Oturum biçiminin ayırıcıları — yalnız public format() çıktısından türetilir (TR "1.234.567,5" → grup "." ondalık ",").
  function ayiricilar() {
    if (!oAyirici) {
      var aIsaret = String(bicim().format(1234567.5)).replace(/\d/g, "").split("");
      oAyirici = {
        ondalik: aIsaret.length ? aIsaret[aIsaret.length - 1] : ".",
        grup: aIsaret.length > 1 ? aIsaret[0] : null
      };
    }
    return oAyirici;
  }

  function isaretsiz(s) { return s.replace(/^[+\-−]/, ""); }
  function bosluksuz(s) { return s.replace(/\s/g, ""); }

  // Kullanıcının yazdığı metin → OData'ya gidecek kanonik sayı dizgisi ya da null (ayrıştırılamadı).
  function metindenSayi(s) {
    var q = bosluksuz(s === null || s === undefined ? "" : String(s));
    if (!q) { return null; }
    var o = ayiricilar();
    var sKalan = q.split(o.ondalik).join("");
    if (o.grup) { sKalan = sKalan.split(o.grup).join(""); }
    if (!/^[+\-−]?\d+$/.test(sKalan)) { return null; }          // harf, %, kısaltma, birden çok işaret → geçersiz
    var aParca = q.split(o.ondalik);
    if (aParca.length > 2) { return null; }
    var v = bicim().parse(q);
    if (typeof v !== "string" || !/^-?\d+(\.\d+)?$/.test(v)) { return null; }
    if (o.grup && aParca[0].indexOf(o.grup) !== -1) {
      var sYeniden = bosluksuz(String(bicim().format(v.split(".")[0])));
      if (isaretsiz(sYeniden) !== isaretsiz(aParca[0])) { return null; }
    }
    return v;
  }

  return { metindenSayi: metindenSayi };
});
