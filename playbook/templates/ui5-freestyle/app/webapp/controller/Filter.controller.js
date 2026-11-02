sap.ui.define([
  "com/example/alan/uygulama/controller/BaseController",
  "sap/ui/comp/valuehelpdialog/ValueHelpDialog",
  "sap/ui/comp/filterbar/FilterBar",
  "sap/m/SearchField",
  "sap/ui/table/Column",
  "sap/m/Column",
  "sap/m/ColumnListItem",
  "sap/m/Label",
  "sap/m/Text",
  "sap/ui/model/Filter",
  "sap/ui/model/FilterOperator",
  "sap/m/MessageBox",
  "sap/m/MessageToast",
  "com/example/alan/uygulama/util/TokenValidator",
  "com/example/alan/uygulama/util/Config",
  "com/example/alan/uygulama/util/SurumParca"
], function (BaseController, ValueHelpDialog, FilterBar, SearchField,
             UiColumn, MColumn, ColumnListItem, MLabel, MText, Filter, FilterOperator,
             MessageBox, MessageToast, TV, Config, SurumParca) {
  "use strict";

  // ============================================================================================
  // SEÇİM EKRANI — SELECT-OPTIONS paritesi + harf-duyarsız "içeren" (std/03 §10.0.1, FE-32, FE-50)
  //  · Her MultiInput: addValidator (yazılı metin → token, VH token'ıyla AYNI anlam — util/TokenValidator)
  //  · Kod alanında yazılan ve VH koşul değerleri BÜYÜK harf (cfg.upper) · $metadata MaxLength aşımı token olmaz
  //  · Listele kapısı: token'a dönüşmemiş metin kalan alan varsa çağrı YOK + alan adlı hata (sessiz yok sayma yasak)
  //  · VH "Tamam": alanda kalan yazılı metin kaybolmaz (_absorbText)
  //  · caseSensitive parametresi HİÇBİR Filter'a verilmez (gateway toupper/tolower → HTTP 400)
  // Sürüme bağlı TEK nokta: çok satırlı yapıştırma (SurumParca.yapistirmaBagla — UI5-özel olay kullanır,
  // bu yüzden ortak gövdede DEĞİL, surum/<v>/ parçasında).
  // ============================================================================================

  var VH = Config.FIELDS;

  // Token metni HAM tutulur: util/TokenValidator token'ı setter'larla kurar (ayar ayrıştırıcısından geçmez ⇒ "{" / "}"
  // bağlama sözdizimi sayılmaz, kaçış gerekmez). Validator'a gelen metnin kaçışlı olup olmadığı SÜRÜME BAĞLIDIR
  // (1.120 kaçışlar, 1.71 kaçışlamaz — ölçüm surum/<v>/webapp/util/SurumParca.js) ⇒ SurumParca.dogrulayiciMetni ham
  // biçime getirir. Yapıştırma satırları (_validateOnPaste texts) iki sürümde de HAMDIR ⇒ olduğu gibi girer.

  return BaseController.extend("com.example.alan.uygulama.controller.Filter", {

    onInit: function () {
      Object.keys(VH).forEach(function (sId) {
        var oMI = this.byId(sId);
        oMI.addValidator(function (oArgs) {
          return this._typedToken(sId, SurumParca.dogrulayiciMetni(oArgs.text), null);
        }.bind(this));
        SurumParca.yapistirmaBagla(oMI,
          function (sLine, aBad) { return this._pasteLine(sId, sLine, aBad); }.bind(this),
          function (aBad) { this._pasteReport(aBad); }.bind(this));
      }, this);
      this._readMaxLengths();
    },

    // Alan uzunlukları: ana entity'nin $metadata MaxLength'i. Okunamazsa Config.FIELDS yedekleri kalır.
    _readMaxLengths: function () {
      var oModel = this.getOwnerComponent().getModel();
      if (!oModel || !oModel.metadataLoaded) { return; }
      oModel.metadataLoaded().then(function () {
        var oMeta = oModel.getMetaModel();
        return oMeta.loaded().then(function () {
          var oES = oMeta.getODataEntitySet(Config.ENTITY.replace(/^\//, ""));
          var oET = oES && oMeta.getODataEntityType(oES.entityType);
          (oET && oET.property || []).forEach(function (p) {
            Object.keys(VH).forEach(function (sId) {
              if (VH[sId].prop === p.name && p.maxLength) { VH[sId].maxLen = parseInt(p.maxLength, 10) || VH[sId].maxLen; }
            });
          });
        });
      }).catch(function () { /* yedek değerler kalır */ });
    },

    onDateChange: function (oEvent) {
      var oDR = oEvent.getSource(), oUi = this.getModel("ui");
      if (oEvent.getParameter("valid") === false) {
        oDR.setValueState("Error");
        oDR.setValueStateText(this.i18n("msg.dateInvalid"));
        oUi.setProperty("/filter/dateFrom", null);
        oUi.setProperty("/filter/dateTo", null);
        this._dateInvalid = true;
        return;
      }
      this._dateInvalid = false;
      oDR.setValueState("None");
      oUi.setProperty("/filter/dateFrom", oDR.getDateValue());
      oUi.setProperty("/filter/dateTo", oDR.getSecondDateValue());
    },

    onClear: function () {
      this.getModel("ui").setProperty("/filter", { ranges: {}, dateFrom: null, dateTo: null });
      this.byId("fDate").setValue("");
      this.byId("fDate").setValueState("None");
      this._dateInvalid = false;
      Object.keys(VH).forEach(function (sId) {
        var oMI = this.byId(sId);
        oMI.removeAllTokens(); oMI.setValue(""); oMI.setValueState("None");
      }, this);
    },

    // ── MultiInput token değişimi → ui>/filter/ranges/<prop> ──
    onTokenUpdate: function (oEvent) {
      var oMI = oEvent.getSource();
      oMI.setValueState("None");
      setTimeout(function () { this._syncTokens(oMI); }.bind(this), 0);   // tokenUpdate değişiklikten ÖNCE ateşlenir
    },
    onTokenTextLive: function (oEvent) { oEvent.getSource().setValueState("None"); },

    // Reddedilen yazılı metnin neden METNİ (yoksa null): TV.parse reason → i18n.
    _rejectText: function (cfg, r) {
      if (r.reason === "op") { return this.i18n("msg.opNotTyped"); }
      if (r.reason === "comma") { return this.i18n("msg.singleValue"); }
      if (r.reason === "range") { return this.i18n("msg.rangeNotTyped"); }
      if (r.reason === "long") { return this.i18n("msg.termTooLong", [cfg.maxLen]); }
      if (r.reason === "inner") { return this.i18n("msg.wildcardInner"); }
      if (r.reason === "star") { return this.i18n("msg.wildcardOnly"); }
      return null;
    },

    // Yazılı metin → token (validator gövdesi). null dönerse metin alanda kalır; Listele kapısı onu yok saymaz.
    // aBad doluysa (yapıştırma) mesaj satır başına verilmez, toplu uyarıda söylenir.
    _typedToken: function (sId, sText, aBad) {
      var cfg = VH[sId], oMI = this.byId(sId), r = TV.parse(cfg, sText), sMsg;
      if (!r.ok) {
        sMsg = this._rejectText(cfg, r);
        if (aBad) { if (sMsg) { aBad.push({ text: String(sText || "").trim(), msg: sMsg }); } }
        else if (sMsg) { MessageToast.show(sMsg); }
        return null;
      }
      if (TV.isDup(cfg, oMI.getTokens(), r)) {
        if (!aBad) {
          // UI5 token dönmeyince metni alanda bırakır; değer zaten token olduğu için metin temizlenir.
          setTimeout(function () {
            if (String(oMI.getValue() || "").trim().toUpperCase() === String(sText || "").trim().toUpperCase()) { oMI.setValue(""); }
          }, 0);
        }
        return null;
      }
      return TV.toToken(cfg, r);
    },

    // Yapıştırılan TEK satır (SurumParca çağırır, HAM metin): aynı token kurucudan geçer; geçerli → public addToken.
    _pasteLine: function (sId, sLine, aBad) {
      var oTok = this._typedToken(sId, sLine, aBad);
      if (oTok) {
        this.byId(sId).addToken(oTok);
        this._syncTokens(this.byId(sId));
      }
    },

    // Geçersiz yapıştırma satırları: tek kalıcı uyarıda değer + neden (sessiz kayıp YOK).
    _pasteReport: function (aBad) {
      var mSeen = {}, aU = [], aTxt, MAX = 20;
      (aBad || []).forEach(function (b) {
        var k = b.text.toUpperCase();
        if (!mSeen[k]) { mSeen[k] = true; aU.push(b); }
      });
      if (!aU.length) { return; }
      aTxt = aU.slice(0, MAX).map(function (b) { return b.text + " — " + b.msg; });
      if (aU.length > MAX) { aTxt.push(this.i18n("msg.pasteMore", [aU.length - MAX])); }
      MessageBox.warning(this.i18n("msg.pasteInvalid", [aU.length]) + "\n\n" + aTxt.join("\n"));
    },

    // VH "Tamam" sonrası alanda kalan yazılı metin: geçerliyse token olur, tekrarsa eklenmez; token olamayan metin kaybolmaz.
    _absorbText: function (oMI) {
      var sId = oMI.getId().split("--").pop(), cfg = VH[sId], s = String(oMI.getValue() || "").trim(), r, sMsg;
      if (!s) { return true; }
      r = TV.parse(cfg, s);
      if (r.ok) {
        if (!TV.isDup(cfg, oMI.getTokens(), r)) { oMI.addToken(TV.toToken(cfg, r)); }
        oMI.setValue("");
        return true;
      }
      sMsg = this._rejectText(cfg, r);
      if (sMsg) { MessageToast.show(sMsg); }
      oMI.setValueState("Error");
      return false;
    },

    // Listele kapısı: token'a dönüşmemiş metin kalan alanlar (etiket listesi).
    _untokenizedFields: function () {
      var aLeft = [];
      Object.keys(VH).forEach(function (sId) {
        var oMI = this.byId(sId), s = oMI ? String(oMI.getValue() || "").trim() : "", r;
        if (!s || !oMI.getEnabled()) { return; }
        r = TV.parse(VH[sId], s);
        if (r.ok && TV.isDup(VH[sId], oMI.getTokens(), r)) { oMI.setValue(""); oMI.setValueState("None"); return; }
        oMI.setValueState("Error");
        aLeft.push(this.i18n(VH[sId].lbl));
      }, this);
      return aLeft;
    },

    // ── F4: generic ValueHelpDialog (değer tablosu + "Koşulları tanımla") ──
    onVH: function (oEvent) { this._openVH(oEvent.getSource()); },

    _openVH: function (oMI) {
      var sId = oMI.getId().split("--").pop();
      var cfg = VH[sId];
      if (!cfg) { return; }
      var that = this;
      var bHasTable = !!cfg.set;
      var sTitle = this.i18n(cfg.i18n);

      var oVHD = new ValueHelpDialog({
        title: sTitle,
        supportRanges: true,
        supportRangesOnly: !bHasTable,
        key: cfg.key || cfg.prop,
        descriptionKey: cfg.text || cfg.prop,
        ok: function (oEv) {
          oMI.setTokens(oEv.getParameter("tokens") || []);
          oMI.setValueState("None");
          that._absorbText(oMI);
          that._syncTokens(oMI);
          oVHD.close();
        },
        cancel: function () { oVHD.close(); },
        afterClose: function () { oVHD.destroy(); }
      });
      this.getView().addDependent(oVHD);
      oVHD.setRangeKeyFields([{ key: cfg.prop, label: sTitle, type: "string" }]);
      oVHD.setTokens(oMI.getTokens());

      if (bHasTable) {
        var oVHTable = null;
        var oSearch = new SearchField({
          search: function (oEv) { that._applyVHSearch(oVHTable, cfg, oEv.getParameter("query")); }
        });
        oVHD.setFilterBar(new FilterBar({
          advancedMode: true, filterBarExpanded: false, showGoOnFB: false, basicSearch: oSearch
        }));
        oVHD.getTableAsync().then(function (oTable) {
          oVHTable = oTable;
          oTable.setModel(that.getOwnerComponent().getModel());
          if (oTable.bindRows) {
            oTable.addColumn(new UiColumn({
              label: new MLabel({ text: sTitle }),
              template: new MText({ wrapping: false, text: "{" + cfg.key + "}" })
            }));
            oTable.addColumn(new UiColumn({
              label: new MLabel({ text: that.i18n("flt.value") }),
              template: new MText({ wrapping: false, text: "{" + cfg.text + "}" })
            }));
            oTable.bindRows({ path: cfg.set });
          } else {
            oTable.addColumn(new MColumn({ header: new MLabel({ text: sTitle }) }));
            oTable.addColumn(new MColumn({ header: new MLabel({ text: that.i18n("flt.value") }) }));
            oTable.bindItems({
              path: cfg.set,
              template: new ColumnListItem({ cells: [new MText({ text: "{" + cfg.key + "}" }), new MText({ text: "{" + cfg.text + "}" })] })
            });
          }
          oVHD.update();
        });
      }
      oVHD.open();
    },

    // VH değer tablosu sunucu tarafı arama (harf duyarsız): düz Contains/StartsWith/EndsWith, caseSensitive YOK.
    _applyVHSearch: function (oTable, cfg, sQuery) {
      if (!oTable) { return; }
      var oBinding = oTable.getBinding("rows") || oTable.getBinding("items");
      if (!oBinding) { return; }
      var p = this._parseSearchTerm(sQuery);
      if (!p) { oBinding.filter([]); return; }
      oBinding.filter([new Filter({
        filters: [new Filter(cfg.key, p.operator, p.value), new Filter(cfg.text, p.operator, p.value)],
        and: false
      })]);
    },
    _parseSearchTerm: function (sRaw) {
      var q = (sRaw || "").trim();
      if (!q) { return null; }
      var bLead = q.charAt(0) === "*", bTrail = q.charAt(q.length - 1) === "*";
      var sVal = q.replace(/\*/g, "");
      if (!sVal) { return null; }
      var op;
      if (bLead && bTrail) { op = FilterOperator.Contains; }
      else if (bTrail) { op = FilterOperator.StartsWith; }
      else if (bLead) { op = FilterOperator.EndsWith; }
      else { op = FilterOperator.Contains; }
      return { operator: op, value: sVal };
    },

    // MultiInput token'ları → ui>/filter/ranges/<prop> (etkin aralık; VH ve yazılı token aynı yorumlanır).
    _syncTokens: function (oMI) {
      var cfg = VH[oMI.getId().split("--").pop()];
      if (!cfg) { return; }
      var aOut = (oMI.getTokens() || []).map(function (oTok) { return TV.effective(cfg, oTok); });
      this.getModel("ui").setProperty("/filter/ranges/" + cfg.prop, aOut);
    },

    onList: function () {
      var aLeft = this._untokenizedFields();
      if (aLeft.length) {                                   // sessiz yok sayma YASAK (std/03 §10.0.1 madde 5)
        MessageBox.error(this.i18n("msg.untokenized", [aLeft.join(", ")]));
        return;
      }
      if (this._dateInvalid) {
        MessageBox.error(this.i18n("msg.dateInvalid"));
        return;
      }
      Object.keys(VH).forEach(function (sId) { this._syncTokens(this.byId(sId)); }, this);
      this.navTo("list");
    }
  });
});
