sap.ui.define([
  "com/example/alan/uygulama/controller/BaseController",
  "com/example/alan/uygulama/util/TablePersonalizer",
  "com/example/alan/uygulama/util/Config",
  "com/example/alan/uygulama/util/SurumParca",
  "sap/ui/model/Filter",
  "sap/ui/model/FilterOperator",
  "sap/ui/model/Sorter",
  "sap/m/MessageToast",
  "sap/m/MessageBox",
  "sap/ui/export/Spreadsheet",
  "sap/ui/export/library",
  "sap/base/Log"
], function (BaseController, TablePersonalizer, Config, SurumParca, Filter, FilterOperator, Sorter,
             MessageToast, MessageBox, Spreadsheet, exportLibrary, Log) {
  "use strict";

  var EdmType = exportLibrary.EdmType;

  // VH koşul operatörü → FilterOperator (dahil / hariç). Yazılı ve VH token'ı aynı tablodan geçer.
  var OP_MAP = {
    EQ:         { inc: FilterOperator.EQ,         exc: FilterOperator.NE },
    BT:         { inc: FilterOperator.BT,         exc: FilterOperator.NB },
    Contains:   { inc: FilterOperator.Contains,   exc: FilterOperator.NotContains },
    StartsWith: { inc: FilterOperator.StartsWith, exc: FilterOperator.NotStartsWith },
    EndsWith:   { inc: FilterOperator.EndsWith,   exc: FilterOperator.NotEndsWith },
    GT:         { inc: FilterOperator.GT,         exc: FilterOperator.LE },
    GE:         { inc: FilterOperator.GE,         exc: FilterOperator.LT },
    LT:         { inc: FilterOperator.LT,         exc: FilterOperator.GE },
    LE:         { inc: FilterOperator.LE,         exc: FilterOperator.GT }
  };

  function rangeToFilter(sProp, oR) {
    var oMap = OP_MAP[oR.operation] || OP_MAP.EQ;
    var sOp = oR.exclude ? oMap.exc : oMap.inc;
    var v1 = (oR.value1 !== null && oR.value1 !== undefined) ? oR.value1 : oR.key;
    if (v1 === null || v1 === undefined || v1 === "") { return null; }
    if (sOp === FilterOperator.BT || sOp === FilterOperator.NB) {
      if (oR.value2 === null || oR.value2 === undefined || oR.value2 === "") { return null; }
      return new Filter(sProp, sOp, v1, oR.value2);
    }
    return new Filter(sProp, sOp, v1);   // caseSensitive parametresi YOK (FE-32)
  }

  // Kolon meta'sı — List.view.xml kolon id'leriyle (colId) birebir. type: string | numeric | date
  function columnsMeta(t) {
    return [
      ["SalesOrder",        "cSalesOrder",   "fld.salesOrder",   "string"],
      ["SalesOrganization", "cSalesOrg",     "fld.salesOrg",     "string"],
      ["Customer",          "cCustomer",     "fld.customer",     "string"],
      ["CustomerName",      "cCustomerName", "fld.customerName", "string"],
      ["Material",          "cMaterial",     "fld.material",     "string"],
      ["DocumentDate",      "cDocumentDate", "fld.date",         "date"],
      ["NetAmount",         "cNetAmount",    "fld.netAmount",    "numeric"]
    ].map(function (r) {
      return { key: r[0], path: r[0], colId: r[1], text: t(r[2]), type: r[3] };
    });
  }

  return BaseController.extend("com.example.alan.uygulama.controller.List", {

    onInit: function () {
      var oTable = this.byId("listTable");
      // Sürüme bağlı parçalar (surum/<v>/webapp/util/SurumParca.js) — ortak gövde bu iki API'yi DOĞRUDAN kullanmaz.
      SurumParca.satirModu(oTable, 10);
      SurumParca.bosDurum(oTable, {
        title: this.i18n("list.emptyTitle"),
        description: this.i18n("list.emptyText"),
        ctaText: this.i18n("btn.changeFilter"),
        onCta: function () { this.navTo("filter"); }.bind(this)
      });

      this._perso = new TablePersonalizer({
        table: oTable,
        persoKey: Config.PERSO_KEY,
        columns: columnsMeta(this.i18n.bind(this)),
        bundle: this.getResourceBundle(),
        baseFilters: this._buildFilters.bind(this),
        variantService: Config.VARIANT
      });

      this.getRouter().getRoute("list").attachPatternMatched(this._onMatched, this);

      // Grid veri isteği backend'de patlarsa V2 grid SESSİZCE boş kalır → ana entity isteğinin hatası gösterilir.
      var oModel = this.getOwnerComponent().getModel();
      if (oModel && oModel.attachRequestFailed) { oModel.attachRequestFailed(this._onRequestFailed, this); }
    },

    onExit: function () {
      if (this._perso) { this._perso.destroy(); }
      var oModel = this.getOwnerComponent().getModel();
      if (oModel && oModel.detachRequestFailed) { oModel.detachRequestFailed(this._onRequestFailed, this); }
    },

    // YALNIZ grid'in kendi okuma isteği: GET <servis>/<ENTITY> + (sorgu | son). Aynı entity'nin anahtarlı okuması
    // ("<ENTITY>('1')", değişiklik ekranı), alt yolu ("<ENTITY>/to_X") ve yazma istekleri (POST/MERGE/DELETE) kendi
    // ekranlarında raporlanır — burada yakalanırsa kaydetme hatası liste hatası diye İKİNCİ kutuda görünür.
    // Olay parametreleri url + method (V2 ODataModel _createEventInfo; 1.71.85 ve 1.120.52'de aynı). 200 + 0 kayıt hata DEĞİLDİR.
    _gridIstegiMi: function (o) {
      var sYol = String(o.url || "").split("?")[0];
      var sSet = Config.ENTITY.replace(/^\//, "");
      if (String(o.method || "GET").toUpperCase() !== "GET") { return false; }
      return sYol.slice(-(sSet.length + 1)) === "/" + sSet;
    },

    _onRequestFailed: function (oEvent) {
      var o = oEvent.getParameters ? oEvent.getParameters() : {};
      if (!this._gridIstegiMi(o)) { return; }
      var oResp = o.response || {};
      var iStatus = parseInt(oResp.statusCode, 10) || 0;
      if (iStatus && iStatus < 400) { return; }
      if (this._bErrorOpen) { return; }
      this._bErrorOpen = true;
      var that = this;
      MessageBox.error(this.i18n("msg.dataError", [this.parseError(oResp)]), {
        onClose: function () { that._bErrorOpen = false; }
      });
    },

    // Rebind sıralamayı TAŞIMAZ (kolon göstergesi "Descending" derken veri sırasız kalır) → kolonlardan topla.
    // "Kolon sıralı mı" sorusu SÜRÜME BAĞLIDIR (sortOrder varsayılanı 1.71'de "Ascending", 1.120'de "None") →
    // SurumParca.siraliMi. Doğrudan sortOrder karşılaştırması 1.71'de HER kolonu sıralı sayar.
    _collectSorters: function (oTable) {
      var aCols = oTable.getSortedColumns().slice();
      oTable.getColumns().forEach(function (oCol) {
        if (aCols.indexOf(oCol) !== -1) { return; }
        if (!SurumParca.siraliMi(oCol) || !oCol.getSortProperty()) { return; }
        aCols.push(oCol);
      });
      return aCols.map(function (oCol) {
        return new Sorter(oCol.getSortProperty(), oCol.getSortOrder() === "Descending");
      });
    },

    _onMatched: function () {
      var oTable = this.byId("listTable");
      this._perso.resetColumnFilters();                     // önceki aramanın bayat kolon filtreleri taşınmasın
      oTable.bindRows({
        path: Config.ENTITY,
        parameters: { countMode: "Inline" },
        filters: this._buildFilters(),                      // seçim ekranı $filter'ı bind anında (tek istek)
        sorter: this._collectSorters(oTable),
        // Kayıt sayısı başlığı: binding'in dataReceived olayı (iki sürümde de var; V2 ODataListBinding uzunluğu
        // olaydan ÖNCE yazar). Hata yanıtında da ateşlenir → başlık bayat sayıda kalmaz.
        events: { dataReceived: this._onDataReceived.bind(this) }
      });
    },

    _tokensToFilter: function (sProp) {
      var aR = this.getModel("ui").getProperty("/filter/ranges/" + sProp) || [];
      var aInc = [], aExc = [];
      aR.forEach(function (oR) {
        var oF = rangeToFilter(sProp, oR);
        if (oF) { (oR.exclude ? aExc : aInc).push(oF); }
      });
      var aParts = [];
      if (aInc.length === 1) { aParts.push(aInc[0]); }
      else if (aInc.length > 1) { aParts.push(new Filter({ filters: aInc, and: false })); }
      aExc.forEach(function (oF) { aParts.push(oF); });
      if (!aParts.length) { return null; }
      return aParts.length === 1 ? aParts[0] : new Filter({ filters: aParts, and: true });
    },

    // Base $filter = seçim ekranı alanları (AND) + tarih aralığı (BT). Tarih sınırlarının İKİSİ de seçilen takvim
    // gününün UTC gece yarısıdır (BaseController.utcGun, FE-45) — yerel gece yarısı bir önceki günü gönderir.
    _buildFilters: function () {
      var aF = [];
      Object.keys(Config.FIELDS).forEach(function (sId) {
        var oF = this._tokensToFilter(Config.FIELDS[sId].prop);
        if (oF) { aF.push(oF); }
      }, this);
      var f = this.getModel("ui").getProperty("/filter") || {};
      var dFrom = this.utcGun(f.dateFrom), dTo = this.utcGun(f.dateTo);
      if (dFrom && dTo) { aF.push(new Filter(Config.DATE_PROP, FilterOperator.BT, dFrom, dTo)); }
      return aF;
    },

    _onDataReceived: function () {
      var oBinding = this.byId("listTable").getBinding("rows");
      this.getModel("ui").setProperty("/listTitle", this.i18n("list.count", [oBinding ? oBinding.getLength() : 0]));
    },

    onRefresh: function () {
      var oBinding = this.byId("listTable").getBinding("rows");
      if (oBinding) { oBinding.refresh(); }
    },

    onColumns: function () { this._perso.openColumns(); },

    onOpen: function (oEvent) {
      var oCtx = oEvent.getSource().getBindingContext();
      if (oCtx) { this.navTo("change", { key: encodeURIComponent(oCtx.getProperty(Config.CHANGE.key)) }); }
    },

    // Excel: filtreye uyan TÜM satırlar (binding'den), kapsam sorulur (Görünür / Tüm kolonlar) — std/03 §16 madde 4.
    onExportExcel: function () {
      var oRowBinding = this.byId("listTable").getBinding("rows");
      if (!oRowBinding) { return; }
      var that = this;
      MessageBox.show(this.i18n("exp.scopeMsg"), {
        icon: MessageBox.Icon.QUESTION,
        title: this.i18n("btn.excel"),
        actions: [this.i18n("exp.visible"), this.i18n("exp.all"), MessageBox.Action.CANCEL],
        onClose: function (sAction) {
          if (!sAction || sAction === MessageBox.Action.CANCEL) { return; }
          that._doExport(oRowBinding, sAction === that.i18n("exp.all"));
        }
      });
    },

    _doExport: function (oRowBinding, bAll) {
      var mEdm = { numeric: EdmType.Number, date: EdmType.Date, string: EdmType.String };
      var aCols = this._perso.getColumnsForExport(bAll).map(function (c) {
        return { label: c.label, property: c.property, type: mEdm[c.kind] || EdmType.String };
      });
      // dataSource bir ListBinding OLAMAZ: 1.71.85 Spreadsheet yalnız URL dizgisi / dizi / {dataUrl} nesnesi kabul
      // eder (sap/ui/export/Spreadsheet-dbg.js:431-444); binding dalı 1.73'te geldi (1.120.52 processDataSource
      // "@since 1.73"). İki sürümde geçerli biçim = 1.120'nin binding'den kendi kurduğu nesne (1.120.52 :567-589):
      // getDownloadUrl → servis URL'i + model URL parametreleri (sap-client) + $format + AKTİF $orderby/$filter
      // (seçim ekranı + kolon başlığı filtreleri — 1.71.85 ODataListBinding-dbg.js:1128-1150 · 1.120.52 :1473-1501).
      var sUrl = oRowBinding.getDownloadUrl("json");
      if (!sUrl) {
        // 1.120.52 ODataListBinding-dbg.js:1477-1479 Filter.NONE'da null · :1500 çözülmemiş yolda boş — sessiz dönüş YOK.
        Log.warning("Excel aktarımı: getDownloadUrl boş döndü (binding yolu çözülmedi ya da filtre tüm satırları dışlıyor).",
          String(oRowBinding.getPath && oRowBinding.getPath()), "ui5-freestyle-sablon.List");
        MessageToast.show(this.i18n("exp.noUrl"));
        return;
      }
      var oSheet = new Spreadsheet({
        workbook: { columns: aCols },
        dataSource: {
          type: "odata",
          dataUrl: sUrl,
          serviceUrl: this.getOwnerComponent().getManifestEntry("/sap.app/dataSources/mainService/uri"),
          headers: oRowBinding.getModel().getHeaders(),
          // count yalnız uzunluk KESİNSE verilir. 1.120'nin kendi kuralı (1.120.52 ExportUtils-dbg.js:1408-1425
          // getCountFromBinding) ÖNCE binding.getCount()'a bakar; V2 ODataListBinding.getCount (1.120.52
          // ODataListBinding-dbg.js:2259-2266) isLengthFinal() değilse undefined, kesinse getLength() − inaktif yaratılmış
          // satır döner. getCount 1.71.85'te YOK (ListBinding.getCount `@since 1.93.0`; 1.71.85 ListBinding-dbg.js ve V2
          // ODataListBinding-dbg.js 0 eşleşme) ⇒ ortak gövde isLengthFinal() ? getLength() kullanır;
          // şablon inaktif satır yaratmadığı için iki değer aynıdır. Kesin değilken getLength tahmindir (+eşik). 1.71.85
          // sap/ui/export/js/XLSXExportUtils.js count'u okuma ÜST SINIRI sayar (min(count, 1e6)); count yoksa boş
          // sayfa gelene kadar okur ve öncesinde satır sayısı bilinmediği için uyarı penceresi açar.
          count: oRowBinding.isLengthFinal() ? oRowBinding.getLength() : undefined,
          useBatch: false
        },
        fileName: Config.EXPORT_FILE,
        worker: false
      });
      var that = this;
      oSheet.build().then(function () {
        MessageToast.show(that.i18n("msg.exportOk"));
        oSheet.destroy();
      }, function () {
        oSheet.destroy();
      });
    }
  });
});
