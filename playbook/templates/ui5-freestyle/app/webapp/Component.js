sap.ui.define([
  "sap/ui/core/UIComponent",
  "sap/ui/model/json/JSONModel",
  "com/example/alan/uygulama/model/models",
  "com/example/alan/uygulama/util/SurumParca"
], function (UIComponent, JSONModel, models, SurumParca) {
  "use strict";

  // std/03 §4: manifest-güdümlü bileşen; ODataModel burada KURULMAZ (manifest yönetir).
  // JSONModel define bağımlılığı olarak alınır (global `sap.ui.model.json.JSONModel` async/strict'te fırlatır — std/03 §2.5).
  return UIComponent.extend("com.example.alan.uygulama.Component", {
    metadata: {
      manifest: "json",
      // Arayüz listesi SÜRÜME BAĞLI: sap.ui.core.IAsyncContentCreation @since 1.89 (std/03 §4 ZORUNLU, 1.71'de YOK)
      // ⇒ surum/<v>/webapp/util/SurumParca.js `bilesenArayuzleri` verir. Async rootView/routing manifest'te iki sürümde de açık.
      interfaces: SurumParca.bilesenArayuzleri
    },

    init: function () {
      UIComponent.prototype.init.apply(this, arguments);
      this.setModel(models.createDeviceModel(), "device");
      // "ui" modeli TAM ŞEKİLLE kurulur (playbook §K3): alt yollar sonradan setProperty ile güncellenir.
      this.setModel(new JSONModel({ busy: false, listTitle: "", filter: { ranges: {}, dateFrom: null, dateTo: null } }), "ui");
      this.getRouter().initialize();
    }
  });
});
