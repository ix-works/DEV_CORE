sap.ui.define([
  "sap/ui/model/Filter",
  "sap/ui/model/FilterOperator",
  "./Sayi",
  "./Tarih"
], function (Filter, FilterOperator, Sayi, Tarih) {
  "use strict";

  // ============================================================================================
  // Kolon başlığı filtresi — koşul modeli ve OData çevirici (std/03 §10.0.1 "Kolon filtresi", bug-checklist FE-32 (e)).
  // Saf modül: DOM'suz, uygulama ad alanından bağımsız (bağımlılıklar GÖRELİ: ./Sayi, ./Tarih) ⇒ aynen kopyalanabilir.
  //
  // Koşullar YALNIZ Filtre… penceresinden verilir (util/KolonFiltrePenceresi); kolon menüsündeki kutu DÜZ ARAMADIR.
  // Kutuya elle koşul yazımı (`!=x`, `a..b`, `>5`, `x*` …) ayrıştırılmaz, reddedilir (kutuDugumu → "kosulYazimi").
  //
  //   kosulListesi(sTur)                        → koşul kodları (İLK ELEMAN varsayılandır)
  //   kosulDugumu(sOp, sDeger, sDeger2, sTur)   → { ok:true, dugum, kosul } | { ok:false, neden, alan }   (pencere)
  //                                               neden: "bos" | "sayi" | "tarih" | "zaman" | "uygunsuz"; alan: 1 | 2 (hatalı değer alanı)
  //   kutuDugumu(sMetin, sTur)                  → { ok:true, bos:true } | { ok:true, dugum, kosul } | { ok:false, neden }   (kutu)
  //                                               neden: "kosulYazimi" | "sayi" | "tarih" | "zaman"
  //   imza(dugum)                               → anlamsal kanonik dizgi (aynı anlamlı girişler aynı imzayı verir)
  //   toFilter(sProp, dugum)                    → sap.ui.model.Filter
  //   terimVaryantlari(sTerim)                  → Türkçe i/İ/ı/I varyant kümesi
  //
  // sTur: "string" | "numeric" | "date" | "time". Bilinmeyen tür "string" gibi işlenir. Saat ("time") yalnız Eşittir alır;
  // "SS:DD[:ss]" / "PT09H53M28S" Edm.Time ISO süresine ("PT09H53M28S") çevrilir (ham yazım sunucuda HTTP 400 "Invalid token" verir).
  //
  // Düğüm: { op, tur, deger, deger2 }
  //   op: CONTAINS STARTS ENDS NOTCONTAINS NOTSTARTS NOTENDS (yalnız metin) · EQ NE LT LE GT GE BT
  //   deger: metin → dize · sayı → Sayi.metindenSayi kanonik dizgisi ("-1250.5") · tarih → UTC gece yarısı Date · saat → "PT09H53M00S"
  // Koşul ("kosul"): { op, v, v2 } — kullanıcının değeri (tarihte "yyyy-MM-dd"); pencerenin dolu açılması ve kutu gösterimi içindir.
  //
  // Pencere değeri HARFİ HARFİNE alınır: `*`, `..`, baştaki `=`/`!` joker ya da operatör DEĞİLDİR (başlar/biter/içerir ayrı koşuldur).
  //
  // ⛔ caseSensitive:false KULLANILMAZ (/IWBEP toupper/tolower'ı HTTP 400 ile reddeder, SAP Note 1797736; FE-32 (a));
  // harf-duyarsızlık sunucudadır (içerir/başlar/biter: substringof…). Sunucu davranışı için bkz. terimVaryantlari.
  // ⛔ SUNUCU OTORİTEDİR: kolon filtresinin anlamı (harf büyüklüğü, ALPHA/birim dönüşümü, boş/NULL alan, ilk-tarih, NULL ondalık,
  //   `<`/`>`/aralık karşılaştırması) alan türüne göre SUNUCUDA belirlenir; istemci bunu AYNEN taklit EDEMEZ.
  //   Bu modülde bu yüzden istemci eşdeğeri (predicate) YOKTUR; tek çıktı `toFilter` (OData $filter).
  // ============================================================================================

  function tamam(oDugum, oKosul) { return { ok: true, dugum: oDugum, kosul: oKosul }; }
  function hata(sNeden, iAlan) { return { ok: false, neden: sNeden, alan: iAlan }; }

  // Koşul kodları — pencere açılır listesinin sırası (ilk eleman = varsayılan).
  var KOSUL_METIN = ["CONTAINS", "EQ", "NE", "STARTS", "ENDS", "NOTCONTAINS", "NOTSTARTS", "NOTENDS", "LT", "LE", "GT", "GE", "BT"];
  var KOSUL_SIRALI = ["EQ", "NE", "LT", "LE", "GT", "GE", "BT"];
  var KOSUL_SAAT = ["EQ"];

  function kolonTuru(sTur) {
    return (sTur === "numeric" || sTur === "date" || sTur === "time") ? sTur : "string";
  }

  function kosulListesi(sTur) {
    var s = kolonTuru(sTur);
    return (s === "time" ? KOSUL_SAAT : (s === "string" ? KOSUL_METIN : KOSUL_SIRALI)).slice();
  }

  // Saat yazımı → Edm.Time ISO süresi ("PT09H53M28S") | null (geçersiz). Kabul: "SS:DD" · "SS:DD:ss" · "PTxxHxxMxxS" (sunucunun kendi biçimi).
  // "SS:DD" saniyeyi 00 kabul eder (tam eşitlik: 09:53 = 09:53:00; aralık DEĞİL). Saat 0–23, dakika/saniye 0–59.
  // Neden: ham yazım ("09:53:28") sunucuya time'09:53:28' olarak gider ve /IWBEP "Invalid token" HTTP 400 verir (liste boşalır).
  function zamanCoz(sMetin) {
    var sH, sM, sS, m = /^(\d{1,2}):(\d{2})(?::(\d{2}))?$/.exec(sMetin);
    if (m) { sH = m[1]; sM = m[2]; sS = m[3] || "0"; }
    else {
      m = /^PT(\d{1,2})H(\d{1,2})M(\d{1,2})S$/i.exec(sMetin);
      if (!m) { return null; }
      sH = m[1]; sM = m[2]; sS = m[3];
    }
    if (+sH > 23 || +sM > 59 || +sS > 59) { return null; }
    function iki(x) { return ("0" + (+x)).slice(-2); }
    return "PT" + iki(sH) + "H" + iki(sM) + "M" + iki(sS) + "S";
  }

  // Tek değer ayrıştırma: { ok:true, v, g } (v = düğüm değeri, g = koşulda saklanan metin) | { ok:false, neden }
  // Tarih SIKI (util/Tarih — olmayan gün sonraki aya KAYMAZ), sayı oturum dilinin biçimiyle (util/Sayi — OData'ya kanonik dizgi):
  // ham metin hiçbir türde filtre değeri OLMAZ (yalnız metin kolonunda metin kendisidir).
  function degerCoz(sMetin, sTur) {
    if (sTur === "numeric") {
      var sSayi = Sayi.metindenSayi(sMetin);
      return sSayi === null ? { ok: false, neden: "sayi" } : { ok: true, v: sSayi, g: sMetin };
    }
    if (sTur === "date") {
      var dGun = Tarih.metindenGun(sMetin);
      return dGun === null ? { ok: false, neden: "tarih" } : { ok: true, v: dGun, g: dGun.toISOString().slice(0, 10) };
    }
    if (sTur === "time") {
      var sPt = zamanCoz(sMetin);
      return sPt === null ? { ok: false, neden: "zaman" } : { ok: true, v: sPt, g: sMetin };
    }
    return { ok: true, v: sMetin, g: sMetin };
  }

  function kirp(s) { return (s === null || s === undefined ? "" : String(s)).trim(); }

  // Pencere: koşul + değer(ler) → düğüm. Değerler harfi harfine alınır (joker/operatör yorumu YOK).
  function kosulDugumu(sOp, sDeger, sDeger2, sTur) {
    var sKolon = kolonTuru(sTur);
    if (kosulListesi(sKolon).indexOf(sOp) < 0) { return hata("uygunsuz", 1); }
    var bBt = (sOp === "BT");
    var s1 = kirp(sDeger), s2 = bBt ? kirp(sDeger2) : "";
    if (!s1) { return hata("bos", 1); }
    if (bBt && !s2) { return hata("bos", 2); }
    var o1 = degerCoz(s1, sKolon);
    if (!o1.ok) { return hata(o1.neden, 1); }
    var oDugum = { op: sOp, tur: sKolon, deger: o1.v }, oKosul = { op: sOp, v: o1.g, v2: "" };
    if (bBt) {
      var o2 = degerCoz(s2, sKolon);
      if (!o2.ok) { return hata(o2.neden, 2); }
      oDugum.deger2 = o2.v;
      oKosul.v2 = o2.g;
    }
    return tamam(oDugum, oKosul);
  }

  // Kutu = düz arama: metinde İÇERİR · sayı/tarih/saatte EŞİTTİR. Koşul yazımı (baştaki `=` `!` `<` `>` `*`, `..`, metnin
  // herhangi bir yerinde `*`) reddedilir: koşullar yalnız Filtre… penceresinden verilir.
  var KOSUL_YAZIMI = /^[=!<>*]|\.\.|\*/;

  function kutuDugumu(sMetin, sTur) {
    var s = kirp(sMetin);
    if (!s) { return { ok: true, bos: true }; }
    if (KOSUL_YAZIMI.test(s)) { return hata("kosulYazimi"); }
    var sKolon = kolonTuru(sTur);
    var sOp = (sKolon === "string") ? "CONTAINS" : "EQ";
    var o = degerCoz(s, sKolon);
    if (!o.ok) { return hata(o.neden); }
    return tamam({ op: sOp, tur: sKolon, deger: o.v }, { op: sOp, v: o.g, v2: "" });
  }

  // Anlamsal imza: düğümün (op, tür, kanonik değer[ler]) dizgisi — kanonik değerleri eşit girişler (kutu "ab" ↔ pencere İçerir "ab",
  // ya da aynı gün farklı yazılmış tarih) aynı imzayı verir; yazılan metne BAKILMAZ.
  function imza(oDugum) {
    function d(v) {
      if (v instanceof Date) { return v.toISOString().slice(0, 10); }
      // sayı: sondaki sıfırlar anlam taşımaz ("1250,5" ≡ "1.250,50") — imza anlamsal eşitliği ölçer
      if (oDugum.tur === "numeric" && typeof v === "string" && /^[+\-−]?\d+\.\d+$/.test(v)) { return v.replace(/0+$/, "").replace(/\.$/, ""); }
      return v === undefined ? null : v;
    }
    return JSON.stringify([oDugum.op, oDugum.tur, d(oDugum.deger), d(oDugum.deger2)]);
  }

  // ── Türkçe i/İ/ı/I — SUNUCU DAVRANIŞI (substringof; bir tüketici projenin SAP Gateway'inde ölçüldü — başka sistemlerde ÖLÇÜLMEDİ,
  // DB harf sıralamasına bağlıdır): {i, I, ı} AYNI sınıf, "İ" AYRI sınıf. Veride iki biçim de bulunur ⇒ metin kolonunda terim DÖRT
  // biçimde aranır: 1) orijinal · 2) i-sınıfı tümü "I" · 3) i-sınıfı tümü "İ" · 4) Türkçe büyük harf eşlemesi (yalnız i→İ, ı→I).
  // Tekilleştirilir. toLocale* KULLANILMAZ (makine yerel ayarına bağlı olur).
  // ⚠ Uygulamada aynı varyant mantığını taşıyan başka bir yardımcı (ör. değer yardımı araması) varsa gövdeler AYNI tutulur.
  function terimVaryantlari(sTerim) {
    var s = String(sTerim);
    var a = [s];
    var sTr = s.replace(/i/g, "İ").replace(/ı/g, "I");
    [s.replace(/[iIıİ]/g, "I"), s.replace(/[iIıİ]/g, "İ"), sTr].forEach(function (v) {
      if (a.indexOf(v) < 0) { a.push(v); }
    });
    return a;
  }

  // ── OData karşılıkları ──
  var OP_METIN = {
    CONTAINS: FilterOperator.Contains, STARTS: FilterOperator.StartsWith, ENDS: FilterOperator.EndsWith,
    NOTCONTAINS: FilterOperator.NotContains, NOTSTARTS: FilterOperator.NotStartsWith, NOTENDS: FilterOperator.NotEndsWith
  };
  var OP_KARSILASTIR = {
    EQ: FilterOperator.EQ, NE: FilterOperator.NE,
    LT: FilterOperator.LT, LE: FilterOperator.LE, GT: FilterOperator.GT, GE: FilterOperator.GE
  };

  function birlestir(aFiltre, bVe) {
    return aFiltre.length === 1 ? aFiltre[0] : new Filter({ filters: aFiltre, and: bVe });
  }

  function toFilter(sProp, oDugum) {
    var sOp = oDugum.op;
    if (sOp === "BT") { return new Filter(sProp, FilterOperator.BT, oDugum.deger, oDugum.deger2); }
    if (oDugum.tur !== "string") { return new Filter(sProp, OP_KARSILASTIR[sOp], oDugum.deger); }   // sayı/tarih/saat

    if (OP_METIN[sOp]) {                           // içerir ailesi: varyantlar OR · içermez ailesi: varyant olumsuzları AND
      var bOlumsuz = sOp.indexOf("NOT") === 0;
      return birlestir(terimVaryantlari(oDugum.deger).map(function (v) {
        return new Filter(sProp, OP_METIN[sOp], v);
      }), bOlumsuz);
    }
    if (sOp === "EQ" || sOp === "NE") {            // tam eşitlik: EQ varyantları OR · NE varyantları AND (sunucu `eq`/`ne` — sunucu otorite)
      return birlestir(terimVaryantlari(oDugum.deger).map(function (v) {
        return new Filter(sProp, OP_KARSILASTIR[sOp], v);
      }), sOp === "NE");
    }
    return new Filter(sProp, OP_KARSILASTIR[sOp], oDugum.deger);   // < <= > >= (metin): varyant uygulanmaz
  }

  return {
    kosulListesi: kosulListesi,
    kosulDugumu: kosulDugumu,
    kutuDugumu: kutuDugumu,
    imza: imza,
    toFilter: toFilter,
    terimVaryantlari: terimVaryantlari
  };
});
