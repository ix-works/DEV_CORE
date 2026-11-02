---
applies_to: [s4_private]
layer: L3
scope: project-wide
type: template
---
# Varyant servisi — backend referansı (RAP, S/4HANA)

`app/webapp/util/TablePersonalizer.js` düzen varyantlarını (kolon görünürlüğü + genişlik + sıra) bir
OData V2 servisinde kullanıcı başına saklar. Bu klasör, o servisin **çalışan bir kurulumundan alınmış**
kaynak kopyasıdır (demo adlandırma `ZSD000_*`). Yeni bir sistemde objeler **kopyalanmaz**, bu dosyalar
referans alınarak o sistemin paketinde ve adlandırmasında yaratılır (ADR 0005-D: etiketler projenin
`master_language`'inde, tam).

| Dosya | Obje | Not |
|---|---|---|
| `ZSD000_T_UIVAR.tabl.abap` | şeffaf tablo | anahtar `variant_uuid` (`sysuuid_x16`); `config` = `abap.string(0)` (JSON düzen) |
| `ZSD000_I_UI_VARIANT.ddls.cds` | kök view entity | `where username = $session.user` ⇒ kullanıcı yalnız kendi varyantını görür |
| `ZSD000_I_UI_VARIANT.bdef` | managed BDEF | `numbering : managed` · `determination setAdmin on save` · `mapping` |
| `ZSD000_C_UI_VARIANT.ddls.cds` + `.bdef` | projeksiyon | `use create/update/delete` |
| `ZCL_SD000_UI_VARIANT.clas.abap` + `.ccimp.abap` | davranış sınıfı | `setAdmin`: oluşturmada kullanıcı + zaman damgaları; `mt_done` koruması determinasyonun kendi `MODIFY`'ıyla yeniden tetiklenmesini keser |

## UI ile sözleşme

| UI tarafı (`util/Config.js` → `VARIANT`) | Backend |
|---|---|
| `serviceUrl` = `/sap/opu/odata/sap/<SRVB_ADI>/` | servis bağlaması (OData V2, UI) |
| `entitySet` = `/<C_VIEW_ADI>` | projeksiyon view adı |
| `nameMaxLen` = `14` | `variant_name` tipi `variant` (CHAR 14) |
| okuma süzgeci `ReportId eq <persoKey>` | `report` alanı (`programm`) |

## Doğrulanmamış kısımlar

- **Servis tanımı (SRVD) ve servis bağlaması (SRVB) bu klasörde YOK** — kaynağı alınan kurulumun deposunda
  da bulunmuyordu. Tanım: projeksiyon entity'sini açığa çıkaran tek satırlık bir SRVD + OData V2 UI bağlaması.
  Adlar ve yayınlama adımı **DOĞRULANMADI**; yaratırken `playbook/` altındaki RAP servis reçetesine bakılır.
- **ECC / UI5 1.71:** RAP ve CDS view entity S/4HANA ister. 1.71 UI'ı ECC üzerinde koşuyorsa varyant servisi
  başka yolla (ör. SEGW) kurulmalıdır — bu yol **DOĞRULANMADI**. Servis hiç yoksa `TablePersonalizer`
  açılışta `Log.warning` yazar ve varyantları tarayıcının `localStorage`'ında tutar (cihaza özel).
