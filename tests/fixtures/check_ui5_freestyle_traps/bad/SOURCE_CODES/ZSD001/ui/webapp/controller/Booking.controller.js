sap.ui.define([
    "sap/ui/core/mvc/Controller"
], function (Controller) {
    "use strict";

    return Controller.extend("zsd001.controller.Booking", {
        onCreateContainerPress: function () {
            var oModel = this.getView().getModel();
            // V2 composition nav adi RAP'te _Container'dir, OData V2'de to_Container olur.
            var oContext = oModel.createEntry("_Container", {
                properties: this._getNewContainerData()
            });
            this._oCreatedContext = oContext;
        },

        _getNewContainerData: function () {
            return { ContainerNo: "", SealNo: "" };
        }
    });
});
