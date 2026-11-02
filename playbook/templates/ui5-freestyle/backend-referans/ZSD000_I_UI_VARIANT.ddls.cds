@AccessControl.authorizationCheck: #NOT_REQUIRED
@EndUserText.label: 'UI Kolon Varyant'
@Metadata.allowExtensions: true
define root view entity ZSD000_I_UI_VARIANT
  as select from zsd000_t_uivar
{
  key variant_uuid as VariantUuid,
      username      as Username,
      report        as ReportId,
      variant_name  as VariantName,
      is_default    as IsDefault,
      config        as Config,
      created_by    as CreatedBy,
      created_at    as CreatedAt,
      changed_at    as ChangedAt
}
where username = $session.user
