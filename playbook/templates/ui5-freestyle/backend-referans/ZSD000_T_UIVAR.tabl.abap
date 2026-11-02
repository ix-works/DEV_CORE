@EndUserText.label : 'UI Kolon Varyant Deposu'
@AbapCatalog.enhancement.category : #NOT_EXTENSIBLE
@AbapCatalog.tableCategory : #TRANSPARENT
@AbapCatalog.deliveryClass : #A
@AbapCatalog.dataMaintenance : #RESTRICTED
define table zsd000_t_uivar {
  key mandt        : mandt not null;
  key variant_uuid : sysuuid_x16 not null;
  username         : xubname;
  report           : programm;
  variant_name     : variant;
  is_default       : xfeld;
  config           : abap.string(0);
  created_by       : xubname;
  created_at       : timestampl;
  changed_at       : timestampl;
}
