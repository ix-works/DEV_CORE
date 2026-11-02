@AccessControl.authorizationCheck: #NOT_REQUIRED
@EndUserText.label: 'UI Kolon Varyant'
@Metadata.allowExtensions: true
define root view entity ZSD000_C_UI_VARIANT
  as projection on ZSD000_I_UI_VARIANT
{
  key VariantUuid,
      Username,
      ReportId,
      VariantName,
      IsDefault,
      Config,
      CreatedBy,
      CreatedAt,
      ChangedAt
}
