sap.ui.define([
  "sap/ui/core/format/DateFormat"
], function (DateFormat) {
  "use strict";

  // ============================================================================================
  // Tarih-yalnız alan (Edm.DateTime + display-format=Date, arkada DATS) yardımcıları — bug-checklist FE-45.
  // V2 ODataModel tarihi $filter'a ve gövdeye UTC olarak yazar (1.71.85 ve 1.120.52 sap/ui/model/odata/ODataUtils
  // "Edm.DateTime" dalı: format(oDate, true)); gateway UTC değerin GÜN kısmını alır. Bu yüzden gönderilen her
  // tarih-yalnız değer, kastedilen takvim gününün UTC gece yarısı olmalıdır. İki giriş yolu vardır:
  //   · kullanıcının seçtiği/yazdığı gün → YEREL gece yarısı (DatePicker, DateRangeSelection, DateFormat.parse)
  //   · backend'den okunan değer       → zaten UTC gece yarısı (V2 Edm.DateTime)
  // utcGun ikisini de doğru güne taşır: değer tam UTC gece yarısıysa UTC parçaları korunur (UTC'nin batısında
  // yerel parçalar bir ÖNCEKİ günü verir — okunup değiştirilmeden geri yazılan tarih kayardı); değilse yerel
  // parçalar alınır. Yerel gece yarısı yalnız ofset 0 olan dilimde UTC gece yarısına denk gelir ve orada iki
  // yorum aynı günü verir ⇒ karışma yok.
  // ============================================================================================

  var oYerelBicim = null;

  function utcGun(d) {
    if (!(d instanceof Date) || isNaN(d.getTime())) { return null; }
    if (d.getUTCHours() === 0 && d.getUTCMinutes() === 0 && d.getUTCSeconds() === 0 && d.getUTCMilliseconds() === 0) {
      return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
    }
    return new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  }

  // Kullanıcının yazdığı metin → takvim günü (UTC gece yarısı) ya da null (ayrıştırılamadı).
  // Ayrıştırma oturum dilinin biçimiyle yapılır: DateFormat.getDateInstance() varsayılanı "medium" + yedek
  // biçimler short · medium · yyyy-MM-dd · yyyyMMdd (1.71.85 DateFormat-dbg.js:62-70 · 1.120.52 :90-98) ⇒
  // grid'in gösterdiği biçim de, kısa sayısal biçim de kabul edilir. Ham metin ASLA filtre değeri yapılmaz:
  // ODataUtils onu new Date(<metin>) ile çevirir ve "02.11.2026" ay/gün yer değiştirmiş bir güne SESSİZCE gider.
  // strictParsing ZORUNLU: varsayılan ayrıştırma taşan günü bir sonraki aya kaydırır ("31.11.2026" → 1 Aralık,
  // "00.11.2026" → 1 Kasım; tarayıcıda 1.71.85 ve 1.120.52'de ölçüldü) ⇒ olmayan bir gün SESSİZCE başka güne
  // filtre olur. strictParsing iki sürümde var ve yedek biçimlere de geçer (parse → fallback.parse(…, bStrict):
  // 1.71.85 DateFormat-dbg.js:2019-2020,2085 · 1.120.52 :2895-2896,2968).
  function metindenGun(s) {
    var q = (s === null || s === undefined ? "" : String(s)).trim();
    if (!q) { return null; }
    if (!oYerelBicim) { oYerelBicim = DateFormat.getDateInstance({ strictParsing: true }); }
    var d = oYerelBicim.parse(q);
    return (d instanceof Date && !isNaN(d.getTime())) ? utcGun(d) : null;
  }

  return { utcGun: utcGun, metindenGun: metindenGun };
});
