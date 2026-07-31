@AbapCatalog.sqlViewName: 'ZSD001V'
@AbapCatalog.compiler.compareFilter: true
@AccessControl.authorizationCheck: #CHECK
@EndUserText.label: 'Siparis Görünümü'
"Bu ABAP tarzi yorum CDS'te GECERSIZ -- SAP sessizce reddeder
define view ZSD001_I_Order
  as select from zsd001_ord
{
      key order_id   as OrderId,
          description as Description,
          created_by  as CreatedBy
}
