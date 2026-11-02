sap.ui.define([], function () {
  "use strict";

  // ============================================================================================
  // UYGULAMAYA ÖZEL TEK AYAR NOKTASI — şablonu kopyalayınca İLK burayı doldur (README §2).
  // Buradaki ZSD001_* adları std/03'teki DEMO adlarıdır; gerçek servisin canlı $metadata'sıyla
  // değiştirilmeden uygulama çalışmaz (`check_ui_odata_refs.py` ile statik karşılaştır — playbook §H).
  // ============================================================================================
  return {
    // Ana liste entity set'i (manifest "mainService" içinde).
    ENTITY: "/ZSD001_C_LIST",

    // Rapor kimliği: TablePersonalizer'ın localStorage anahtarı + varyant servisindeki ReportId.
    // Varyant tablosunda alan CHAR40 (`backend-referans/`), uygulama başına TEKİL olmalı.
    PERSO_KEY: "ZSD001_LIST",

    // DB varyant servisi (backend-referans/README.md). Servis yoksa / okunamazsa TablePersonalizer
    // localStorage'a düşer ve bunu Log.warning ile yazar (sessiz düşme yok). Servis HİÇ kurulmayacaksa
    // VARIANT: null yap — o zaman da açılışta bir kez Log.warning yazılır.
    VARIANT: {
      serviceUrl: "/sap/opu/odata/sap/ZSD000_UI_VARIANT_O2/",
      entitySet: "/ZSD000_C_UI_VARIANT",
      nameMaxLen: 14                     // VariantName = CHAR14 (backend-referans tablo tanımı)
    },

    // Seçim ekranı alanları (SELECT-OPTIONS pariteli; std/03 §10.0.1). Anahtar = Filter.view'daki MultiInput id'si.
    //   prop  : ana entity'deki $filter alanı · set/key/text: VH değer kümesi (set yoksa yalnız "Koşulları tanımla")
    //   i18n  : VH başlığı · lbl: alan etiketi (token'a dönüşmemiş metin hatasında alan adı)
    //   upper : KOD alanı (domain LOWERCASE boş) → yazılan değer ve VH koşul değerleri BÜYÜK harfe çevrilir
    //           (ayrımı $metadata / DDIC'ten ÖLÇ — tahmin etme)
    //   maxLen: $metadata MaxLength yedeği (Filter.controller açılışta $metadata'dan okur)
    //   defaultOp: düz token operatörü (yoksa EQ); kısmi kod araması isteniyorsa "Contains"
    FIELDS: {
      fSalesOrg: { prop: "SalesOrganization", set: "/ZSD001_I_SALESORG_VH", key: "SalesOrganization",
                   text: "SalesOrganizationName", i18n: "vh.salesOrg", lbl: "fld.salesOrg", upper: true, maxLen: 4 },
      fCustomer: { prop: "Customer", set: "/ZSD001_I_CUSTOMER_VH", key: "Customer",
                   text: "CustomerName", i18n: "vh.customer", lbl: "fld.customer", upper: true, maxLen: 10 },
      fMaterial: { prop: "Material", set: "/ZSD001_I_MATERIAL_VH", key: "Material",
                   text: "MaterialName", i18n: "vh.material", lbl: "fld.material", upper: true, maxLen: 40,
                   defaultOp: "Contains" }
    },
    // Tarih aralığı alanı (DateRangeSelection → BT)
    DATE_PROP: "DocumentDate",

    // Kaydetme deseni örneği (Change ekranı): kök entity + V2 composition nav adı (to_X — `_X` DEĞİL, playbook §K2)
    CHANGE: {
      root: "/ZSD001_C_LIST",
      nav: "to_Item",
      child: "/ZSD001_C_LISTITEM",
      key: "SalesOrder",
      childKey: "ItemNo"
    },

    // Excel dosya adı
    EXPORT_FILE: "Liste.xlsx"
  };
});
