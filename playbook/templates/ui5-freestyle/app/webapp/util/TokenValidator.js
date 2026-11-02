sap.ui.define([
  "sap/m/Token",
  "sap/ui/comp/library"
], function (Token, compLibrary) {
  "use strict";

  var RangeOp = compLibrary.valuehelpdialog.ValueHelpRangeOperation;

  // ============================================================================================
  // YAZILI METİN → TOKEN (std/03 §10.0.1 "Yazılı metin → token" · FE-50)
  //
  // MultiInput'a elle yazılan metni (Enter / Tab / odak kaybı) VH'nin ürettiği token'larla AYNI anlamda
  // token'a çevirir. SAF mantıktır: kontrol, mesaj ve model bilmez — neden-kodu döner, mesajı çağıran verir.
  //
  // Token anlamı (Filter.controller `_syncTokens` / List.controller `rangeToFilter` ile birebir):
  //   · düz değer ("1500")      → range verisi YOK; operatör `cfg.defaultOp` (yoksa EQ)  — VH satır seçimiyle aynı
  //   · "x*"  → StartsWith · "*x" → EndsWith · "*x*" → Contains   — range verili token (VH koşul sekmesiyle aynı)
  //   Yeni token türü YOK.
  //
  // `cfg` (Filter.controller VH haritası girdisi):
  //   prop      : $filter alanı (range.keyField)
  //   upper     : true → kod alanı (domain LOWERCASE boş): yazılan değer VE range value1/value2 BÜYÜK harfe çevrilir
  //   maxLen    : $metadata MaxLength — aşan terim token olmaz
  //   defaultOp : düz token operatörü (FE-32)
  //
  // Sürüm: yalnız public API (sap.m.Token, ValueHelpRangeOperation) — 1.71.85 ve 1.120.52 kaynağında var (README §4).
  // ============================================================================================

  function up(cfg, v) {
    if (v === null || v === undefined) { return v; }
    return cfg.upper ? String(v).toUpperCase() : String(v);
  }

  // Yazılı metni çözümler. Dönüş:
  //   { ok:true,  operation, value1, wild }   wild=false → düz token · wild=true → range token
  //   { ok:false, reason }   reason: "empty" | "op" (yazılı koşul işareti) | "comma" (kod alanında virgül) |
  //                                  "range" (aralık metni "...") | "star" (yalnız joker) | "inner" (joker ortada) |
  //                                  "long" (maxLength aşıldı)
  function parse(cfg, sRaw) {
    var t = String(sRaw === null || sRaw === undefined ? "" : sRaw).trim(), bLead, bTrail, v, sOp;
    if (!t) { return { ok: false, reason: "empty" }; }
    // Yazılı koşul işareti düz değer olmaz — hariç/karşılaştırma yalnız VH "Koşulları tanımla" sekmesinden.
    if (/^[!=<>]/.test(t)) { return { ok: false, reason: "op" }; }
    // Kod alanında virgül içeren metin TEK değer değildir ("5, 7" yapıştırma artığı) — reddedilir, nedeni söylenir.
    if (cfg.upper && t.indexOf(",") >= 0) { return { ok: false, reason: "comma" }; }
    // "..." içeren terim (VH aralık token'ının metni) düz değer OLMAZ — aralık yalnız VH "Koşulları tanımla"dan.
    if (t.indexOf("...") >= 0) { return { ok: false, reason: "range" }; }
    t = up(cfg, t);
    bLead = t.charAt(0) === "*";
    bTrail = t.charAt(t.length - 1) === "*";
    v = t.replace(/^\*+/, "").replace(/\*+$/, "");
    if (!v) { return { ok: false, reason: "star" }; }
    // "a*b" sessizce "içerir AB"ye çevrilmez (yazılandan geniş sonuç olurdu) — token olmaz.
    if (v.indexOf("*") >= 0) { return { ok: false, reason: "inner" }; }
    if (cfg.maxLen && v.length > cfg.maxLen) { return { ok: false, reason: "long" }; }
    if (!bLead && !bTrail) {
      return { ok: true, wild: false, operation: cfg.defaultOp || RangeOp.EQ, value1: v };
    }
    sOp = (bLead && bTrail) ? RangeOp.Contains : (bTrail ? RangeOp.StartsWith : RangeOp.EndsWith);
    return { ok: true, wild: true, operation: sOp, value1: v };
  }

  // Token'ı HAM metinle kurar: değerler kurucuya AYAR olarak verilmez, setter'la yazılır. Kurucu ayarındaki dizgi
  // bağlama ifadesi diye ayrıştırılır ("{" / "}" içeren değer bozulur — sap/ui/base/ManagedObject-dbg.js sınıf
  // belgesi, 1.71.85 ve 1.120.52); setter ayrıştırmaz ⇒ kaçış gerekmez, çift kaçış riski yoktur.
  function hamToken(sKey, sText) {
    var oTok = new Token();
    oTok.setKey(sKey);
    oTok.setText(sText);
    return oTok;
  }

  // parse() çıktısından token üretir (yalnız ok:true). Girdi HAM metindir (Filter.controller dogrulayiciMetni).
  function toToken(cfg, d) {
    var oTok, sTxt;
    if (!d.wild) { return hamToken(d.value1, d.value1); }
    sTxt = d.operation === RangeOp.Contains ? ("*" + d.value1 + "*")
      : (d.operation === RangeOp.StartsWith ? (d.value1 + "*") : ("*" + d.value1));
    oTok = hamToken("range_" + d.operation + "_" + d.value1, sTxt);
    oTok.data("range", { exclude: false, operation: d.operation, keyField: cfg.prop, value1: d.value1, value2: "" });
    return oTok;
  }

  // Token → süzgeç kurucunun okuduğu etkin aralık. VH'den gelen (satır seçimi ya da "Koşulları tanımla") ve yazılı
  // token'lar AYNI yoldan geçer; kod alanında value1/value2 büyük harfe çevrilir (backend çevirmez — küçük harf
  // HATASIZ boş sonuç verir).
  function effective(cfg, oTok) {
    var r = oTok.data("range");
    if (r) {
      return {
        key: oTok.getKey(),
        text: oTok.getText(),
        exclude: !!r.exclude,
        operation: r.operation,
        value1: up(cfg, r.value1),
        value2: up(cfg, r.value2)
      };
    }
    return {
      key: oTok.getKey(),
      text: oTok.getText(),
      exclude: false,
      operation: cfg.defaultOp || RangeOp.EQ,
      value1: up(cfg, oTok.getKey()),
      value2: null
    };
  }

  function sig(e) {
    return [e.exclude ? "X" : "I", e.operation, e.value1 === null || e.value1 === undefined ? "" : e.value1,
      e.value2 === null || e.value2 === undefined ? "" : e.value2].join("|");
  }

  // Yazılı metin (parse çıktısı) alandaki bir token'ın TEKRARI mı? Karşılaştırma ANLAM üzerinden (etkin aralık,
  // büyük harfe çevrilmiş): düz "ABC" (defaultOp Contains) ile VH koşul sekmesinden gelen Contains "abc" aynıdır.
  function isDup(cfg, aTokens, d) {
    var s = sig({ exclude: false, operation: d.operation, value1: d.value1, value2: "" });
    return (aTokens || []).some(function (t) { return sig(effective(cfg, t)) === s; });
  }

  return { parse: parse, toToken: toToken, effective: effective, isDup: isDup };
});
