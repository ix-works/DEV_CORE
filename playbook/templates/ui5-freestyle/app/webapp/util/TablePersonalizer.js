sap.ui.define([
  "sap/ui/base/Object",
  "sap/ui/model/Filter",
  "sap/ui/model/FilterOperator",
  "sap/m/Label",
  "sap/m/Input",
  "sap/m/Select",
  "sap/ui/core/Item",
  "sap/m/CheckBox",
  "sap/m/Button",
  "sap/m/Dialog",
  "sap/m/HBox",
  "sap/m/VBox",
  "sap/m/SearchField",
  "sap/m/ScrollContainer",
  "sap/m/ToggleButton",
  "sap/m/MessageBox",
  "sap/m/MessageToast",
  "sap/ui/model/odata/v2/ODataModel",
  "sap/ui/core/Component",
  "sap/base/Log",
  "com/example/alan/uygulama/util/Tarih",
  "com/example/alan/uygulama/util/Sayi"
], function (BaseObject, Filter, FilterOperator, Label, Input,
             Select, CoreItem, CheckBox, Button, Dialog, HBox, VBox,
             SearchField, ScrollContainer, ToggleButton, MessageBox, MessageToast, ODataModel, Component, Log, Tarih, Sayi) {
  "use strict";

  // ============================================================================================
  // TablePersonalizer — sap.ui.table.Table (grid / ALV-tarzı) kişiselleştirme (std/03 §10.0 + §16, ADR 0008)
  //  - Sort/Filter: GRID'in NATIVE kolon menüsünden (sortProperty/filterProperty) → custom kolon menüsü YOK.
  //  - "Kolonlar" göster/gizle penceresi (arama + tümünü seç/kaldır + kaydırma) + varyant çubuğu.
  //  - DB varyant: Config = TAM layout { cols: [ {key, visible, width, index} ] }.
  //  - Excel export için kolon listesi (getColumnsForExport).
  //
  // Kullanım:
  //   new TablePersonalizer({
  //     table: oGrid, persoKey: "<RAPOR_ANAHTARI>", bundle: oResourceBundle,
  //     columns: [{ key, path, colId, text, type: "string"|"numeric"|"date" }],
  //     baseFilters: function () { return [ ...seçim ekranı süzgeçleri... ]; },
  //     defaultHidden: ["<key>"],                       // isteğe bağlı: başlangıçta gizli kolonlar
  //     variantService: { serviceUrl, entitySet, nameMaxLen }   // isteğe bağlı (yoksa yalnız localStorage)
  //   });
  //
  // VARYANT SERVİSİ BAĞIMLILIĞI (Issue: servis yoksa sessiz düşme YOK):
  //   variantService verilmezse ya da servis okunamazsa/yazılamazsa varyantlar tarayıcının localStorage'ında
  //   tutulur ve bu Log.warning ile YAZILIR (bileşen adı LOG_BILESEN). localStorage kayıtları makineye/tarayıcıya
  //   özeldir, başka kullanıcıya/cihaza gitmez.
  //
  // Sürüm: yalnız 1.71.85 kaynağında da var olan API (README §4). Ana modelin `aUrlParams` / `mMetadataUrlParams`
  // alanları UI5-özel alanlardır (std/03 §18.5b "bilinçli istisna") — tip korumalı okunur; alan kaybolursa eski
  // davranışa (çereze) düşer, patlamaz.
  // ============================================================================================

  var LOG_BILESEN = "ui5-freestyle-sablon.TablePersonalizer";

  return BaseObject.extend("com.example.alan.uygulama.util.TablePersonalizer", {

    constructor: function (opts) {
      this._t = opts.table;                      // sap.ui.table.Table
      this._key = opts.persoKey;
      this._cols = opts.columns;                 // [{key,path,colId,text,type}]
      this._t18 = opts.bundle;
      this._baseFilters = opts.baseFilters || function () { return []; };

      var vs = opts.variantService || null;
      this._varSvc = (vs && vs.serviceUrl && vs.entitySet) ? vs : null;
      this._varNameMax = (vs && vs.nameMaxLen) || 14;
      if (!this._varSvc) {
        Log.warning("Varyant servisi parametresi verilmedi — varyantlar yalnız bu tarayıcının localStorage'ında tutulur.",
          "persoKey=" + this._key, LOG_BILESEN);
      }

      // key → sap.ui.table.Column eşlemesi
      this._colById = {};
      var aC = this._t.getColumns();
      this._cols.forEach(function (m) {
        this._colById[m.key] = aC.filter(function (c) {
          return c.getId().split("--").pop() === m.colId;
        })[0];
      }, this);

      // Başlangıçta gizli kolonlar: kayıtlı durum/varyant yoksa ve "Standart" varyantta gizli kalır.
      this._defHidden = {};
      (opts.defaultHidden || []).forEach(function (k) { this._defHidden[k] = true; }, this);

      var st = this._load();
      this._hidden = (st && st.hidden) || Object.assign({}, this._defHidden);     // { key:true }

      // Aktif kolon-başlığı filtreleri: { <filterProperty>: sap.ui.model.Filter }
      this._colFilters = {};
      // Uygulanmakta olan kolon filtresinin kullanıcı metni: { <filterProperty>: "<metin>" } (geçersiz girişte geri çekilir)
      this._colFilterText = {};

      // DB varyant durumu: { <name>: { uuid, name, isDefault, cols:[...] } } — null = servis yok / okunamadı
      this._variants = null;
      // O an grid'e uygulanmış varyantın adı (null = Standart) — açılışta servisteki varsayılan varyant.
      this._aktifVaryant = null;

      this._applyVisibility();

      // Grid NATIVE kolon filtresi → string kolonda düz Contains (substringof; backend harf-duyarsız).
      // caseSensitive parametresi VERİLMEZ (FE-32: gateway toupper/tolower'ı reddeder, HTTP 400).
      this._t.attachFilter(this._onColumnFilter, this);

      // Varyantları servisten yükle, IsDefault varsa otomatik uygula (async).
      this._initVariantsFromService();
    },

    // ── grid native kolon-filtresi → harf-duyarsız (string) ──
    _onColumnFilter: function (oEvent) {
      oEvent.preventDefault();
      var oColumn = oEvent.getParameter("column");
      var sValue  = oEvent.getParameter("value");
      var sProp   = oColumn.getFilterProperty();
      if (!sProp) { return; }

      var v = (sValue === null || sValue === undefined ? "" : String(sValue)).trim();
      var oMeta = this._cols.filter(function (m) { return m.path === sProp; })[0] || {};
      var sType = oMeta.type || "string";
      var oFilter = null, aGecersiz = null;   // [mesaj (önceki filtre yok), mesaj (önceki filtre korundu)]
      if (v) {
        if (sType === "string") {
          var p = this._parseSearchTerm(v);
          if (p) { oFilter = new Filter(sProp, p.operator, p.value); }
        } else if (sType === "date") {
          // Tarih: metin oturum dilinin biçimiyle SIKI ayrıştırılır → takvim gününün UTC gece yarısı (util/Tarih,
          // FE-45). Ham metin filtre YAPILMAZ (ODataUtils new Date(<metin>) → ay/gün kayar, sessiz).
          var dGun = Tarih.metindenGun(v);
          if (dGun) {
            oFilter = new Filter(sProp, FilterOperator.EQ, dGun);
          } else {
            aGecersiz = [this._txt("flt.dateInvalid"), this._txt("flt.dateInvalidKept")];
          }
        } else {
          // Sayı: metin oturum dilinin sayı biçimiyle ayrıştırılır → kanonik dizgi (util/Sayi). Ham metin filtre
          // YAPILMAZ (ODataUtils Edm.Decimal v + "m" → TR "1.250" 1,25 aranır, sessiz).
          var sSayi = Sayi.metindenSayi(v);
          if (sSayi !== null) {
            oFilter = new Filter(sProp, FilterOperator.EQ, sSayi);
          } else {
            aGecersiz = [this._txt("flt.numberInvalid"), this._txt("flt.numberInvalidKept")];
          }
        }
      }
      // Ayrıştırılamayan metin: kolonun ÖNCEKİ geçerli filtresi KORUNUR (binding'e dokunulmaz) ve mesaj bunu söyler.
      // Tarih ve sayı dalı aynı davranır. Menüdeki filtre metni de uygulanmakta olan filtreye geri çekilir.
      if (aGecersiz) {
        var sOnceki = this._colFilterText[sProp];
        if (this._colFilters[sProp] && sOnceki) {
          // fonksiyonlu replace: metindeki "$&" / "$1" özel değiştirme deseni sayılmasın. {1} ÖNCE: geçersiz
          // metin "{1}" içeriyorsa ikinci replace onu değiştirmesin (önceki metin geçerli tarih/sayıdır, süslü parantez taşımaz).
          MessageToast.show(aGecersiz[1].replace("{1}", function () { return sOnceki; })
            .replace("{0}", function () { return v; }));
          oColumn.setFilterValue(sOnceki);
        } else {
          MessageToast.show(aGecersiz[0].replace("{0}", function () { return v; }));
          oColumn.setFilterValue("");
        }
        return;
      }
      if (oFilter) {
        this._colFilters[sProp] = oFilter;
        this._colFilterText[sProp] = v;
        oColumn.setFiltered(true);
        oColumn.setFilterValue(v);
      } else {
        delete this._colFilters[sProp];
        delete this._colFilterText[sProp];
        oColumn.setFiltered(false);
        oColumn.setFilterValue("");
      }
      this._applyAllFilters();
    },

    // Joker → operatör (SELECT-OPTIONS alışkanlığı): '*x*' veya 'x' → Contains · 'x*' → StartsWith · '*x' → EndsWith.
    _parseSearchTerm: function (sRaw) {
      var q = (sRaw || "").trim();
      if (!q) { return null; }
      var bLead  = q.charAt(0) === "*";
      var bTrail = q.charAt(q.length - 1) === "*";
      var sVal = q.replace(/\*/g, "");
      if (!sVal) { return null; }
      var op;
      if (bLead && bTrail) { op = FilterOperator.Contains; }
      else if (bTrail)     { op = FilterOperator.StartsWith; }
      else if (bLead)      { op = FilterOperator.EndsWith; }
      else                 { op = FilterOperator.Contains; }
      return { operator: op, value: sVal };
    },

    // Base filtreler + tüm aktif kolon filtreleri → AND.
    // ⛔ Düz dizi `oBinding.filter([...])`'e verilirse UI5 AYNI path'li filtreleri OR'lar: seçim ekranı token'ı ile
    //   kolon başlığı filtresi aynı alanı süzünce süzgeç daralmak yerine GENİŞLER (bir tüketici projede canlı ölçüldü).
    //   Çözüm: tüm grupları tek AÇIK `and:true` multi-filter'a sarmak (path-bazlı otomatik gruplama uygulanmaz).
    _applyAllFilters: function () {
      var oBinding = this._t.getBinding("rows");
      if (!oBinding) { return; }
      var aGroups = (this._baseFilters() || []).slice();
      Object.keys(this._colFilters).forEach(function (k) {
        aGroups.push(this._colFilters[k]);
      }, this);
      if (!aGroups.length) {
        oBinding.filter([], "Application");
        return;
      }
      var oCombined = (aGroups.length === 1) ? aGroups[0] : new Filter({ filters: aGroups, and: true });
      oBinding.filter(oCombined, "Application");
    },

    _txt: function (s) { return this._t18 ? this._t18.getText(s) : s; },

    _load: function () {
      try {
        var o = JSON.parse(window.localStorage.getItem(this._key));
        return (o && typeof o.hidden === "object") ? o : null;
      } catch (e) { return null; }
    },
    _save: function () {
      try {
        window.localStorage.setItem(this._key, JSON.stringify({ hidden: this._hidden }));
      } catch (e) {
        Log.warning("Kolon görünürlüğü localStorage'a yazılamadı.", String(e), LOG_BILESEN);
      }
    },

    _applyVisibility: function () {
      this._cols.forEach(function (m) {
        var oCol = this._colById[m.key];
        if (oCol) { oCol.setVisible(!this._hidden[m.key]); }
      }, this);
    },

    // Seçim ekranı süzgeci değişince çağrılır — base + aktif kolon filtreleri birlikte.
    refreshFilters: function () {
      this._applyAllFilters();
    },

    // Grid rows yeniden bağlanırken önceki aramanın bayat kolon filtrelerini temizle. filter() ÇAĞIRMAZ
    // (rebind base filtreleri zaten taşır); iç durum + kolon "filtered" işaretini sıfırlar.
    resetColumnFilters: function () {
      var that = this;
      Object.keys(this._colFilters).forEach(function (k) { delete that._colFilters[k]; });
      this._colFilterText = {};
      (this._t.getColumns() || []).forEach(function (oCol) {
        if (oCol.getFiltered && oCol.getFiltered()) { oCol.setFiltered(false); }
        if (oCol.getFilterValue && oCol.getFilterValue()) { oCol.setFilterValue(""); }
      });
    },

    // Excel export için kolon listesi (bAll=true → gizliler dahil)
    getColumnsForExport: function (bAll) {
      return this._cols.filter(function (m) {
        return bAll || !this._hidden[m.key];
      }, this).map(function (m) {
        return { label: m.text, property: m.path, kind: m.type || "string" };
      });
    },

    // ── Varyant modeli ana (manifest) modelin istemci parametrelerini taşır (std/03 §18.5b, FE-48) ──
    //    `sap-client`'sız istek tarayıcının tek `sap-usercontext` çerezine göre yönlenir; aynı tarayıcıda iki client
    //    açıkken yanlış client'a gider. Ana model SAHİP BİLEŞENDEN alınır (onInit'te tablonun modeli henüz yok).
    _mainModel: function () {
      var oOwner = Component.getOwnerComponentFor(this._t);
      return (oOwner && oOwner.getModel()) || this._t.getModel();
    },
    _mainModelClientParams: function () {
      var oMain = this._mainModel();
      var aParams = (oMain && Array.isArray(oMain.aUrlParams)) ? oMain.aUrlParams : [];
      var aFlat = [];
      aParams.forEach(function (s) {
        (String(s || "").split("&")).forEach(function (p) { if (p) { aFlat.push(p); } });
      });
      return aFlat.filter(function (s) { return !/^sap-statistics=/i.test(s); });
    },

    // Lazy OData V2 varyant modeli (backend kullanıcıya göre süzer). Servis parametresi yoksa null.
    _varModel: function () {
      if (!this._varSvc) { return null; }
      if (!this._oVarModel) {
        var aClientParams = this._mainModelClientParams();
        var sUrl = this._varSvc.serviceUrl + (aClientParams.length ? ("?" + aClientParams.join("&")) : "");
        // FE-43 (std/03 §18.5a): ana modelin metadataUrlParams'ı devralınır.
        var oMain = this._mainModel();
        var oMeta = (oMain && oMain.mMetadataUrlParams && typeof oMain.mMetadataUrlParams === "object")
          ? oMain.mMetadataUrlParams : undefined;
        this._oVarModel = new ODataModel(sUrl, {
          useBatch: false,
          defaultBindingMode: "TwoWay",
          metadataUrlParams: oMeta
        });
      }
      return this._oVarModel;
    },

    // localStorage yedeği (servis yok / erişilemez)
    _loadVariants: function () {
      try {
        var o = JSON.parse(window.localStorage.getItem(this._key + "_vars"));
        return (o && typeof o === "object") ? o : {};
      } catch (e) { return {}; }
    },
    _saveVariants: function (o) {
      try {
        window.localStorage.setItem(this._key + "_vars", JSON.stringify(o || {}));
      } catch (e) {
        Log.warning("Varyantlar localStorage'a yazılamadı.", String(e), LOG_BILESEN);
      }
    },
    _fallbackLog: function (sNe, e) {
      Log.warning("Varyant servisi: " + sNe + " — localStorage yedeğine düşüldü.",
        (e && (e.responseText || e.message)) || String(e || ""), LOG_BILESEN);
    },

    // ── Layout (cols: visible+width+index) ↔ Config JSON ──
    _readCurrentLayout: function () {
      var that = this;
      return this._cols.map(function (m) {
        var oCol = that._colById[m.key];
        return {
          key: m.key,
          visible: oCol ? oCol.getVisible() : !that._hidden[m.key],
          width: oCol ? oCol.getWidth() : "",
          index: oCol ? that._t.indexOfColumn(oCol) : -1
        };
      });
    },
    _layoutToConfig: function (aCols) {
      return JSON.stringify({ cols: aCols || [] });
    },
    _configToLayout: function (sConfig) {
      try {
        var o = JSON.parse(sConfig || "{}");
        if (o && Array.isArray(o.cols)) { return o.cols; }
        if (o && o.hidden && typeof o.hidden === "object") {           // eski { hidden:{} } biçimi
          return Object.keys(o.hidden).filter(function (k) { return o.hidden[k]; })
            .map(function (k) { return { key: k, visible: false }; });
        }
        return [];
      } catch (e) { return []; }
    },

    // Bir layout'u (cols) grid'e uygula: visible + width + sıra (index).
    _applyLayout: function (aCols) {
      var that = this;
      if (!aCols || !aCols.length) {
        this._hidden = Object.assign({}, this._defHidden);
        this._cols.forEach(function (m) {
          var oCol = that._colById[m.key];
          if (oCol) { oCol.setVisible(!that._hidden[m.key]); }
        });
        this._syncCheckBoxes();
        this._save();
        return;
      }
      this._hidden = {};
      aCols.forEach(function (c) {
        var oCol = that._colById[c.key];
        if (!oCol) { return; }
        var bVisible = (c.visible !== false);
        oCol.setVisible(bVisible);
        if (!bVisible) { that._hidden[c.key] = true; }
        if (c.width) { oCol.setWidth(c.width); }
      });
      var aOrdered = aCols.filter(function (c) { return typeof c.index === "number" && c.index >= 0; })
        .sort(function (a, b) { return a.index - b.index; });
      aOrdered.forEach(function (c, i) {
        var oCol = that._colById[c.key];
        if (!oCol) { return; }
        if (that._t.indexOfColumn(oCol) !== i) {
          that._t.removeColumn(oCol);
          that._t.insertColumn(oCol, i);
        }
      });
      this._syncCheckBoxes();
      this._save();
    },

    _syncCheckBoxes: function () {
      var that = this;
      if (!this._colCheckBoxes) { return; }
      this._cols.forEach(function (m) {
        var oCb = that._colCheckBoxes[m.key];
        if (oCb) { oCb.setSelected(!that._hidden[m.key]); }
      });
    },

    // Servisten ReportId eq persoKey ile varyantları oku (Promise; servis yoksa/okunamazsa null).
    _readVariantsFromService: function () {
      var that = this;
      return new Promise(function (resolve) {
        var oModel;
        try {
          oModel = that._varModel();
        } catch (e) {
          that._fallbackLog("model kurulamadı", e);
          that._variants = null;
          resolve(null);
          return;
        }
        if (!oModel) { that._variants = null; resolve(null); return; }
        oModel.read(that._varSvc.entitySet, {
          filters: [new Filter("ReportId", FilterOperator.EQ, that._key)],
          success: function (oData) {
            var map = {};
            (oData && oData.results ? oData.results : []).forEach(function (r) {
              map[r.VariantName] = {
                uuid: r.VariantUuid,
                name: r.VariantName,
                isDefault: r.IsDefault === true || r.IsDefault === "X",
                cols: that._configToLayout(r.Config)
              };
            });
            that._variants = map;
            resolve(map);
          },
          error: function (e) {
            that._fallbackLog("okunamadı", e);
            that._variants = null;
            resolve(null);
          }
        });
      });
    },

    _initVariantsFromService: function () {
      var that = this;
      this._readVariantsFromService().then(function (map) {
        if (!map) { return; }              // yedek: localStorage durumu constructor'da uygulandı
        var oDef = null;
        Object.keys(map).forEach(function (sName) {
          if (map[sName].isDefault) { oDef = map[sName]; }
        });
        if (oDef) {
          that._applyLayout(oDef.cols);
          that._aktifVaryant = oDef.name;           // seçim kutusu bunu gösterir (_seciliAnahtar)
          // Pencere zaten açıksa seçim kutusu uygulanan varyantı göstersin ("Standart" değil).
          that._refreshVariantSelect(oDef.name);
        }
      });
    },

    // Pencere açılınca seçim kutusunda gösterilecek anahtar: o an UYGULANMIŞ varyant (açılışta varsayılan).
    // Varsayılan varyant açılışta grid'e uygulanır; kutu "Standart" gösterirse kullanıcı gördüğü düzenin adını
    // bilemez ve "Varsayılan Yap" düğmesi yanlış durumda kalır.
    _seciliAnahtar: function () {
      var sKey = this._aktifVaryant;
      return (sKey && this._variantSource()[sKey]) ? sKey : "__std__";
    },

    // Aktif varyant kaynağı: DB (this._variants) varsa o, yoksa localStorage.
    _variantSource: function () {
      return (this._variants !== null) ? this._variants : this._loadVariants();
    },

    _refreshVariantSelect: function (sSelectKey) {
      if (!this._varSelect) { return; }
      var that = this;
      this._varSelect.destroyItems();
      this._varSelect.addItem(new CoreItem({ key: "__std__", text: this._txt("var.standard") }));
      var o = this._variantSource();
      Object.keys(o).sort().forEach(function (sName) {
        var v = o[sName] || {};
        var sText = v.isDefault ? (sName + " ★") : sName;   // ★ varsayılan
        that._varSelect.addItem(new CoreItem({ key: sName, text: sText }));
      });
      if (sSelectKey) { this._varSelect.setSelectedKey(sSelectKey); }
      this._updateDefaultButton();
    },

    _applyVariant: function (sKey) {
      this._aktifVaryant = (sKey === "__std__") ? null : sKey;
      if (sKey === "__std__") {
        this._applyLayout([]);
      } else {
        var v = this._variantSource()[sKey];
        this._applyLayout((v && v.cols) ? v.cols : []);
      }
      this._updateDefaultButton();
    },

    _updateDefaultButton: function () {
      if (!this._defaultBtn || !this._varSelect) { return; }
      var sKey = this._varSelect.getSelectedKey();
      var o = this._variantSource();
      var v = (sKey && sKey !== "__std__") ? o[sKey] : null;
      this._defaultBtn.setEnabled(!!v);
      this._defaultBtn.setPressed(!!(v && v.isDefault));
    },

    _varEntityPath: function (sUuid) {
      return this._varSvc.entitySet + "(guid'" + sUuid + "')";
    },

    // ── Servis CRUD yardımcıları (her biri Promise döner) ──
    _svcCreateVariant: function (sName, aCols, bDefault) {
      var that = this;
      return new Promise(function (resolve, reject) {
        that._varModel().create(that._varSvc.entitySet, {
          ReportId: that._key,
          VariantName: sName,
          IsDefault: bDefault === true,
          Config: that._layoutToConfig(aCols)
        }, { success: resolve, error: reject });
      });
    },
    _svcUpdateVariant: function (sUuid, oPayload) {
      var that = this;
      return new Promise(function (resolve, reject) {
        that._varModel().update(that._varEntityPath(sUuid), oPayload, {
          merge: true, success: resolve, error: reject
        });
      });
    },
    _svcDeleteVariant: function (sUuid) {
      var that = this;
      return new Promise(function (resolve, reject) {
        that._varModel().remove(that._varEntityPath(sUuid), { success: resolve, error: reject });
      });
    },

    // "Farklı Kaydet" → ad giriş penceresi (CHAR14) + kayıt. Kaydedilen Config = MEVCUT grid layout.
    _openSaveVariantDialog: function () {
      var that = this;
      var oInput = new Input({ width: "100%", placeholder: this._txt("var.name"), maxLength: this._varNameMax });
      var oDlg = new Dialog({
        title: this._txt("var.saveAs"),
        contentWidth: "20rem",
        content: [ new VBox({
          items: [ new Label({ text: this._txt("var.name") }), oInput ]
        }).addStyleClass("sapUiSmallMargin") ],
        beginButton: new Button({
          text: this._txt("var.save"),
          type: "Emphasized",
          press: function () {
            var sName = (oInput.getValue() || "").trim();
            if (!sName || sName === "__std__" || sName.length > that._varNameMax) {
              oInput.setValueState("Error");
              oInput.setValueStateText(that._txt("var.nameInvalid"));
              return;
            }
            var aCols = that._readCurrentLayout();
            var src = that._variantSource();
            var bUsingService = (that._variants !== null);

            var fnFallbackSave = function () {
              var o = that._loadVariants();
              o[sName] = { name: sName, isDefault: false, cols: aCols };
              that._saveVariants(o);
              that._refreshVariantSelect(sName);
              oDlg.close();
            };
            var fnAfterService = function () {
              that._readVariantsFromService().then(function () {
                that._refreshVariantSelect(sName);
                oDlg.close();
              });
            };
            var fnDoSave = function () {
              if (!bUsingService) { fnFallbackSave(); return; }
              var existing = src[sName];
              if (existing && existing.uuid) {
                that._svcUpdateVariant(existing.uuid, { Config: that._layoutToConfig(aCols) })
                  .then(fnAfterService, function (e) { that._fallbackLog("güncellenemedi", e); fnFallbackSave(); });
              } else {
                that._svcCreateVariant(sName, aCols, false)
                  .then(fnAfterService, function (e) { that._fallbackLog("oluşturulamadı", e); fnFallbackSave(); });
              }
            };

            if (Object.prototype.hasOwnProperty.call(src, sName)) {
              MessageBox.confirm(that._txt("var.overwrite").replace("{0}", sName), {
                title: that._txt("var.saveAs"),
                onClose: function (a) { if (a === MessageBox.Action.OK) { fnDoSave(); } }
              });
            } else {
              fnDoSave();
            }
          }
        }),
        endButton: new Button({ text: this._txt("flt.close"), press: function () { oDlg.close(); } }),
        afterClose: function () { oDlg.destroy(); }
      });
      this._t.addDependent(oDlg);
      oDlg.open();
    },

    // "Varsayılan Yap" → seçili varyant IsDefault=true, diğerleri false. MERGE'ler SIRALI (bug-checklist FE-38):
    // önce eski varsayılan(lar) KAPATILIR, sonra yenisi AÇILIR; ilk hatada durulur ve sunucu durumu yeniden okunur.
    // Kısmi başarıda sonuç: kapatma yazıldı + açma yazılamadı ⇒ HİÇ varsayılan yok (açılışta Standart) — iki
    // varsayılan kalamaz. Paralel (Promise.all) gönderimde iki varsayılanlı ara durum mümkündü.
    _setVariantAsDefault: function (sName) {
      var that = this;
      var src = that._variantSource();
      if (!src[sName]) { return; }

      if (that._variants === null) {
        var o = that._loadVariants();
        Object.keys(o).forEach(function (k) { if (o[k]) { o[k].isDefault = (k === sName); } });
        that._saveVariants(o);
        that._refreshVariantSelect(sName);
        return;
      }

      // Yalnız uuid listesi biriktirilir — istek BURADA atılmaz (Promise yürütücüsü senkron çalışır; hazır Promise
      // dizisi = paralel istek). Sıra: kapatmalar → açma.
      var aKapat = [], aAc = [];
      Object.keys(src).forEach(function (k) {
        var v = src[k];
        if (!v || !v.uuid) { return; }
        var bShouldDefault = (k === sName);
        if (!!v.isDefault !== bShouldDefault) {
          (bShouldDefault ? aAc : aKapat).push({ uuid: v.uuid, IsDefault: bShouldDefault });
        }
      });
      var aSira = aKapat.concat(aAc), i = 0;
      var fnReload = function () {
        that._readVariantsFromService().then(function () { that._refreshVariantSelect(sName); });
      };
      var fnSonraki = function () {
        if (i >= aSira.length) { fnReload(); return; }
        var o = aSira[i++];
        that._svcUpdateVariant(o.uuid, { IsDefault: o.IsDefault }).then(fnSonraki, function (e) {
          Log.warning("Varyant servisi: varsayılan ayarlanamadı (" + (i - 1) + "/" + aSira.length
            + " güncelleme yazıldı, kalanlar gönderilmedi).", (e && e.responseText) || String(e || ""), LOG_BILESEN);
          fnReload();
        });
      };
      fnSonraki();
    },

    _deleteVariant: function (sKey) {
      var that = this;
      MessageBox.confirm(this._txt("var.deleteConfirm").replace("{0}", sKey), {
        title: this._txt("var.delete"),
        onClose: function (a) {
          if (a !== MessageBox.Action.OK) { return; }
          var v = that._variantSource()[sKey];
          var fnFallback = function () {
            var o = that._loadVariants();
            delete o[sKey];
            that._saveVariants(o);
            that._refreshVariantSelect("__std__");
            that._applyVariant("__std__");
          };
          var fnAfter = function () {
            that._readVariantsFromService().then(function () {
              that._refreshVariantSelect("__std__");
              that._applyVariant("__std__");
            });
          };
          if (that._variants !== null && v && v.uuid) {
            that._svcDeleteVariant(v.uuid).then(fnAfter, function (e) { that._fallbackLog("silinemedi", e); fnFallback(); });
          } else {
            fnFallback();
          }
        }
      });
    },

    // ── "Kolonlar" göster/gizle penceresi ──
    openColumns: function () {
      var that = this;

      if (this._colDlg) {
        var sSel = this._varSelect ? this._varSelect.getSelectedKey() : "__std__";
        this._readVariantsFromService().then(function () { that._refreshVariantSelect(sSel); });
        if (this._colSearch) { this._colSearch.setValue(""); }
        this._filterColumnCheckBoxes("");
        this._syncCheckBoxes();
        this._colDlg.open();
        return;
      }

      // 1) Varyant çubuğu
      this._varSelect = new Select({ width: "16rem", autoAdjustWidth: false });
      this._varSelect.attachChange(function () { that._applyVariant(that._varSelect.getSelectedKey()); });
      var oVarBar = new HBox({
        alignItems: "Center",
        wrap: "Wrap",                            // dar pencerede "Varsayılan Yap" kesilmesin
        items: [
          new Label({ text: this._txt("var.label"), width: "5rem" }),
          this._varSelect,
          new Button({
            icon: "sap-icon://save", tooltip: this._txt("var.saveAs"),
            press: function () { that._openSaveVariantDialog(); }
          }),
          new Button({
            icon: "sap-icon://delete", tooltip: this._txt("var.delete"),
            press: function () {
              var sKey = that._varSelect.getSelectedKey();
              if (sKey !== "__std__") { that._deleteVariant(sKey); }
            }
          }),
          (this._defaultBtn = new ToggleButton({
            icon: "sap-icon://favorite",
            text: this._txt("var.setDefault"),
            tooltip: this._txt("var.setDefault"),
            enabled: false,
            press: function () {
              var sKey = that._varSelect.getSelectedKey();
              if (sKey === "__std__") { that._updateDefaultButton(); return; }
              that._setVariantAsDefault(sKey);
            }
          }))
        ]
      }).addStyleClass("sapUiTinyMarginBottom");

      // 2) Arama
      this._colSearch = new SearchField({
        width: "100%",
        liveChange: function (oEv) { that._filterColumnCheckBoxes(oEv.getParameter("newValue") || ""); }
      }).addStyleClass("sapUiTinyMarginBottom");

      // 3) Tümünü seç / kaldır
      var oSelectAllBar = new HBox({
        items: [
          new Button({
            text: this._txt("var.selectAll"),
            press: function () {
              that._hidden = {};
              that._cols.forEach(function (m) {
                var oCol = that._colById[m.key];
                if (oCol) { oCol.setVisible(true); }
              });
              that._syncCheckBoxes();
              that._save();
            }
          }),
          new Button({
            text: this._txt("var.deselectAll"),
            press: function () {
              that._cols.forEach(function (m) {
                that._hidden[m.key] = true;
                var oCol = that._colById[m.key];
                if (oCol) { oCol.setVisible(false); }
              });
              that._syncCheckBoxes();
              that._save();
            }
          }).addStyleClass("sapUiTinyMarginBegin")
        ]
      }).addStyleClass("sapUiTinyMarginBottom");

      // 4) Kolon onay kutuları (tam metin)
      this._colCheckBoxes = {};
      var oListBox = new VBox({
        items: this._cols.map(function (m) {
          var oCb = new CheckBox({
            text: m.text,
            selected: !that._hidden[m.key],
            wrapping: true,
            width: "100%",
            select: function (oEv) {
              if (oEv.getParameter("selected")) { delete that._hidden[m.key]; }
              else { that._hidden[m.key] = true; }
              var oCol = that._colById[m.key];
              if (oCol) { oCol.setVisible(!that._hidden[m.key]); }
              that._save();
            }
          });
          that._colCheckBoxes[m.key] = oCb;
          return oCb;
        })
      });
      var oScroll = new ScrollContainer({
        vertical: true, horizontal: false, height: "22rem", width: "100%", content: [oListBox]
      });

      this._colDlg = new Dialog({
        title: this._txt("btn.cols"),
        contentWidth: "36rem",
        draggable: true,
        resizable: true,
        content: [ new VBox({ items: [oVarBar, this._colSearch, oSelectAllBar, oScroll] }).addStyleClass("sapUiSmallMargin") ],
        endButton: new Button({ text: this._txt("flt.close"), press: function () { that._colDlg.close(); } })
      });
      this._t.addDependent(this._colDlg);

      this._refreshVariantSelect(this._seciliAnahtar());
      this._readVariantsFromService().then(function () { that._refreshVariantSelect(that._seciliAnahtar()); });
      this._colDlg.open();
    },

    _filterColumnCheckBoxes: function (sQuery) {
      var that = this;
      var q = (sQuery || "").toLowerCase();
      if (!this._colCheckBoxes) { return; }
      this._cols.forEach(function (m) {
        var oCb = that._colCheckBoxes[m.key];
        if (!oCb) { return; }
        oCb.setVisible(!q || (m.text || "").toLowerCase().indexOf(q) !== -1);
      });
    },

    destroy: function () {
      if (this._t) { this._t.detachFilter(this._onColumnFilter, this); }
      if (this._oVarModel) { this._oVarModel.destroy(); this._oVarModel = null; }
      if (this._colDlg) { this._colDlg.destroy(); this._colDlg = null; }
      BaseObject.prototype.destroy.apply(this, arguments);
    }
  });
});
