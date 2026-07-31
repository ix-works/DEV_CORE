sap.ui.define([
    "sap/ui/core/mvc/Controller",
    "sap/ui/model/Filter",
    "sap/ui/model/FilterOperator"
], function (Controller, Filter, FilterOperator) {
    "use strict";

    return Controller.extend("zsd001.controller.Search", {
        onSearch: function (sQuery) {
            var oBinding = this.byId("idOrderTable").getBinding("rows");
            // NOT: caseSensitive:false /IWBEP'te toupper/tolower uretir -> HTTP 400
            var oFilter = new Filter({
                path: "OrderId",
                operator: FilterOperator.Contains,
                value1: sQuery,
                caseSensitive: false
            });
            oBinding.filter([oFilter]);
        }
    });
});
