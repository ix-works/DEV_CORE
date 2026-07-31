sap.ui.define([
    "sap/ui/core/mvc/Controller"
], function (Controller) {
    "use strict";

    return Controller.extend("zsd001.controller.Booking", {
        onCreateContainerPress: function () {
            var oModel = this.getView().getModel();
            // V2 composition nav adi OData V2'de to_Container olur (RAP _Container degil).
            var oContext = oModel.createEntry("to_Container", {
                properties: this._getNewContainerData()
            });
            this._oCreatedContext = oContext;
        },

        _getNewContainerData: function () {
            return { ContainerNo: "", SealNo: "" };
        }
    });
});
