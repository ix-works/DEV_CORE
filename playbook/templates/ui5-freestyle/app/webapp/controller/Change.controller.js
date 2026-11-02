sap.ui.define([
  "com/example/alan/uygulama/controller/BaseController",
  "com/example/alan/uygulama/util/Config",
  "sap/ui/model/json/JSONModel",
  "sap/m/MessageBox"
], function (BaseController, Config, JSONModel, MessageBox) {
  "use strict";

  // ============================================================================================
  // KAYDETME DESENİ ÖRNEĞİ (playbook/ui-freestyle-odata-v2.md §B kutusu + §K1, checklist UI-ARCH-01..03 / UI-SAVE-*)
  //  · Düzenleme oturumu = JSON tampon "v" { h:{başlık}, d:[kalemler], del:[silinen anahtarlar] } — V2 nav-binding +
  //    createEntry DEĞİL (§B2/§B3). OData yalnız yükle (read $expand → tampon) + kaydet (açık çağrılar).
  //  · Kaydet: YENİ → tek iç içe POST (deep create) · MEVCUT → SIRALI (_runSeq): başlık MERGE → yeni kalem POST →
  //    değişen kalem MERGE (anahtar gövdede YOK) → silinen kalem DELETE. Paralel değil (RAP BO kilit çakışması, §B6).
  //  · Başarı → MessageBox.success, navigasyon OK'ten SONRA (std/03 §7.6). Hata → GERÇEK SAP mesajı (parseError, §B9).
  //  · hasPendingChanges() ön-kapısı YOK (§B7). Boş tarih = null, "" DEĞİL (§K1 b).
  // Bu ekranın ALANLARI uygulamaya özeldir (bespoke) — tekrar kullanılan yalnız akış/plumbing'dir (§K sınırı).
  // ============================================================================================

  var C = Config.CHANGE;
  var HEADER_EDITABLE = ["Description"];               // yalnız düzenlenebilir alanlar gönderilir (§K1 c)
  var ITEM_EDITABLE = ["Material", "Quantity"];

  return BaseController.extend("com.example.alan.uygulama.controller.Change", {

    onInit: function () {
      this.getView().setModel(new JSONModel(this._empty()), "v");
      this.getRouter().getRoute("change").attachPatternMatched(this._onMatched, this);
    },

    // TAM ŞEKİL (§K3) — setData her zaman bu şekille çağrılır.
    _empty: function () {
      return { isNew: false, edit: true, h: {}, d: [], del: [] };
    },

    _rootPath: function (sKey) { return C.root + "('" + String(sKey).replace(/'/g, "''") + "')"; },
    _childPath: function (sKey, sItem) {
      return C.child + "(" + C.key + "='" + String(sKey).replace(/'/g, "''") + "'," + C.childKey + "='" + sItem + "')";
    },

    _onMatched: function (oEvent) {
      var sKey = decodeURIComponent(oEvent.getParameter("arguments").key);
      var oV = this.getView().getModel("v");
      oV.setData(this._empty());
      if (sKey === "new") { oV.setProperty("/isNew", true); return; }
      this._load(sKey);
    },

    // Kaydı backend'den okuyup tamponu TAMAMEN yeniden kurar (açılış + kısmi kaydetme sonrası yeniden eşitleme).
    _load: function (sKey) {
      var oV = this.getView().getModel("v");
      var that = this, mParams = {};
      mParams["$expand"] = C.nav;                            // V2 nav adı to_X (§K2)
      this.getModel("ui").setProperty("/busy", true);
      this.getOwnerComponent().getModel().read(this._rootPath(sKey), {
        urlParameters: mParams,
        success: function (oData) {
          var aItems = (oData[C.nav] && oData[C.nav].results) || [];
          oV.setData({ isNew: false, edit: true, h: oData, d: aItems.map(function (it) {
            var o = {};
            Object.keys(it).forEach(function (k) { if (k !== "__metadata") { o[k] = it[k]; } });
            o._orig = JSON.stringify(ITEM_EDITABLE.map(function (f) { return it[f]; }));
            return o;
          }), del: [] });
          that.getModel("ui").setProperty("/busy", false);
        },
        error: function (oErr) {
          that.getModel("ui").setProperty("/busy", false);
          MessageBox.error(that.i18n("msg.loadFail", [that.parseError(oErr)]));
        }
      });
    },

    onAddItem: function () {
      var oV = this.getView().getModel("v"), a = oV.getProperty("/d").slice();
      a.push({ isNewItem: true, Material: "", Quantity: "" });
      oV.setProperty("/d", a);
    },

    onDeleteItem: function (oEvent) {
      var oV = this.getView().getModel("v");
      var oItem = oEvent.getParameter("listItem").getBindingContext("v").getObject();
      var a = oV.getProperty("/d").filter(function (x) { return x !== oItem; });
      if (!oItem.isNewItem) { oV.setProperty("/del", oV.getProperty("/del").concat([oItem[C.childKey]])); }
      oV.setProperty("/d", a);
    },

    // Aktif input değerini modele işlet (blur) → setTimeout(0) → _save (§B kutusu)
    onSave: function () {
      var oFocus = document.activeElement;
      if (oFocus && oFocus.blur) { oFocus.blur(); }
      setTimeout(this._save.bind(this), 0);
    },

    onCancel: function () { this.onNavBack(); },

    // Gönderilecek alanlar. Tarih alanı (ad "Date" ile biter): boş → null (§K1 b) · Date → takvim gününün UTC gece
    // yarısı (BaseController.utcGun → util/Tarih, FE-45). İki giriş de doğru güne gider: kullanıcının seçtiği gün
    // (YEREL gece yarısı — olduğu gibi gönderilirse UTC'nin doğusunda bir önceki gün KALICI yazılır) ve backend'den
    // okunup DEĞİŞTİRİLMEDEN geri gönderilen değer (zaten UTC gece yarısı — yerel parçalarla çevrilirse UTC'nin
    // batısında bir önceki gün yazılır; utcGun bu değeri UTC parçalarıyla korur).
    // Not: şablonun örnek alan listelerinde (HEADER_/ITEM_EDITABLE) tarih alanı yok — dal, alan eklendiğinde çalışır.
    _pick: function (o, aFields) {
      var that = this, r = {};
      aFields.forEach(function (f) {
        var v = o[f];
        if (/Date$/.test(f)) { v = (v === undefined || v === "" || v === null) ? null : (that.utcGun(v) || v); }
        r[f] = v;
      });
      return r;
    },

    // Tek OData çağrısı → Promise. DİKKAT: Promise yürütücüsü SENKRON çalışır, çağrı ANINDA uçar ⇒ sıralılık için
    // _runSeq'e THUNK (function(done, fail)) verilir; dizide hazır Promise biriktirmek = PARALEL istek.
    _v2: function (sFn) {
      var m = this.getOwnerComponent().getModel(), args = Array.prototype.slice.call(arguments, 1);
      return new Promise(function (res, rej) {
        var mOpt = { success: res, error: rej };
        if (sFn === "update") { mOpt.merge = true; }
        args.push(mOpt);
        m[sFn].apply(m, args);
      });
    },

    // Sıralı async işlemler — her eleman function(done, fail); bir öncekinin bitişi beklenir. İlk hatada DURUR (fail-fast).
    // onFail(oErr, iBasarili): iBasarili = hatadan ÖNCE başarıyla biten çağrı sayısı (>0 ⇒ backend KISMEN yazıldı).
    _runSeq: function (aFns, onDone, onFail, iBasarili) {
      var that = this, n = iBasarili || 0;
      if (!aFns.length) { onDone(); return; }
      aFns[0](function () { that._runSeq(aFns.slice(1), onDone, onFail, n + 1); },
        function (oErr) { onFail(oErr, n); });
    },

    _save: function () {
      var that = this, oV = this.getView().getModel("v"), h = oV.getProperty("/h"), d = oV.getProperty("/d");
      var fnOk = function (sDoc) { that._ok(sDoc || h[C.key]); };
      var fnErr = function (oErr, iBasarili) { that._err(oErr, iBasarili ? h[C.key] : null); };
      this.getModel("ui").setProperty("/busy", true);

      if (oV.getProperty("/isNew")) {
        // YENİ: tek iç içe POST (deep create) — backend erken numaralandırma anahtarı atar (§B4)
        var oBody = this._pick(h, HEADER_EDITABLE);
        oBody[C.nav] = d.map(function (it) { return that._pick(it, ITEM_EDITABLE); });
        this._v2("create", C.root, oBody).then(function (oData) { fnOk(oData && oData[C.key]); }, fnErr);
        return;
      }

      var sKey = h[C.key], aFns = [];
      aFns.push(function (done, fail) { that._v2("update", that._rootPath(sKey), that._pick(h, HEADER_EDITABLE)).then(done, fail); });
      d.forEach(function (it) {
        if (it.isNewItem) {
          aFns.push(function (done, fail) {
            that._v2("create", that._rootPath(sKey) + "/" + C.nav, that._pick(it, ITEM_EDITABLE)).then(done, fail);
          });
        } else if (JSON.stringify(ITEM_EDITABLE.map(function (f) { return it[f]; })) !== it._orig) {
          // DEĞİŞEN mevcut kalem de MERGE alır (§B5); kalem ANAHTARI gövdeye konmaz
          aFns.push(function (done, fail) {
            that._v2("update", that._childPath(sKey, it[C.childKey]), that._pick(it, ITEM_EDITABLE)).then(done, fail);
          });
        }
      });
      oV.getProperty("/del").forEach(function (sItem) {
        aFns.push(function (done, fail) { that._v2("remove", that._childPath(sKey, sItem)).then(done, fail); });
      });
      this._runSeq(aFns, function () { fnOk(sKey); }, fnErr);
    },

    _ok: function (sDoc) {
      var that = this;
      this.getModel("ui").setProperty("/busy", false);
      this.getOwnerComponent().getModel().refresh(true);
      // std/03 §7.6: MessageBox (modal) — navigasyon kullanıcı OK'leyince; Toast + hemen navTo mesajı kaybettirir.
      MessageBox.success(this.i18n("msg.saved", [sDoc]), {
        onClose: function () { that.navTo("list", {}, true); }
      });
    },

    // sKismiAnahtar doluysa sıralı kaydetme YARIDA kaldı: önceki çağrılar backend'e yazıldı. Tampon o hâliyle
    // bırakılırsa ikinci "Kaydet" aynı yeni kalemi YENİDEN POST eder (çift kayıt) ve silinmiş kalemi YENİDEN
    // DELETE eder (404 → kaydetme kalıcı kilitlenir) — bug-checklist FE-38 / FE-29. Bu yüzden hata kutusu
    // kapanınca kayıt backend'den yeniden okunur; kullanıcı kaydedilmeyen kısmı güncel veri üzerinde yeniden girer.
    _err: function (oErr, sKismiAnahtar) {
      var that = this;
      this.getModel("ui").setProperty("/busy", false);
      if (!sKismiAnahtar) {
        MessageBox.error(this.i18n("msg.saveFail", [this.parseError(oErr)]));   // GERÇEK SAP mesajı (§B9)
        return;
      }
      MessageBox.error(this.i18n("msg.saveFailPartial", [this.parseError(oErr)]), {
        onClose: function () { that._load(sKismiAnahtar); }
      });
    }
  });
});
