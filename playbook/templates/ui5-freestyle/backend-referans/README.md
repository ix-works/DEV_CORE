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

## Backend sürüm sınırı

Bu kaynaklar iki sözdizimine dayanır: **CDS view entity** (`define root view entity … as select from`, I-katmanı)
ve **BDEF strict modu** (`strict ( 2 );`, iki BDEF'in 2. satırı). İkisi de her S/4HANA sürümünde YOKTUR.

| Backend | Durum | Kanıt |
|---|---|---|
| S/4HANA 2025 | kaynaklar bu sözdizimiyle çalışan bir kurulumdan alındı | bu klasörün alındığı kurulum (§ilk paragraf) |
| S/4HANA 1909 (`SAP_BASIS 754`) | **derlenmez** — `define view entity … as select from` → `Keyword ENTITY not allowed` · `strict ( 2 );` → `Unexpected character "2"`, `strict;` → `"internal \| with" expected` | ADT checkrun, kaydetmeden inline içerik (DEV_CORE Issue #384, 2026-11-02). ⚠ Ölçüm **vekil objelerde**: DDL `root`'suz bir view entity (`as select from t000`), `strict` sistemdeki bir **unmanaged** BDEF'te — şablonun kendi I-DDL'i, managed I-BDEF'i ve `projection;` C-BDEF'i denenmedi |
| 2020 – 2023 | **ÖLÇÜLMEDİ** — hangi sürümde view entity ve `strict ( 2 )` geldiği burada doğrulanmadı | — |

**1909 uyarlaması (ölçülen: reddedilen biçimler + C-projeksiyonunun kabulü; uyarlanmış kaynakların kendisi ve
uçtan uca kurulum ÖLÇÜLMEDİ):**
- I-katmanı: klasik DDIC tabanlı görünüm — `@AbapCatalog.sqlViewName: '<SQL_GORUNUM_ADI>'` +
  `@AbapCatalog.preserveKey: true` + `define root view <AD> as select from …` (`preserveKey` yoksa
  checkrun `"@AbapCatalog.preserveKey: true" missing for entity in BO structure` verir).
- C-katmanı: `define root view entity … as projection on …` **aynen kalır** (1909'da kabul edildi;
  `define root view … as projection on` ise `Keyword ENTITY expected` ile reddedildi).
- İki BDEF'ten `strict ( 2 );` satırı çıkarılır.
- 1909'da **ÖLÇÜLMEDİ:** managed ve `projection;` BDEF'te `strict` reddi (yalnız unmanaged'da ölçüldü) ·
  `preserveKey`'li I-DDL ile `strict`'siz iki BDEF'in temiz derlenmesi · `numbering : managed`,
  `determination … on save`, `authorization master ( global )`, `use create/update/delete` · SRVD/SRVB + OData V2 bağlama.

## Doğrulanmamış kısımlar

- **Servis tanımı (SRVD) ve servis bağlaması (SRVB) bu klasörde YOK** — kaynağı alınan kurulumun deposunda
  da bulunmuyordu. Tanım: projeksiyon entity'sini açığa çıkaran tek satırlık bir SRVD + OData V2 UI bağlaması.
  Adlar ve yayınlama adımı **DOĞRULANMADI**; yaratırken `playbook/` altındaki RAP servis reçetesine bakılır.
- **ECC / UI5 1.71:** RAP ve CDS view entity S/4HANA ister (sürüm sınırı: yukarıdaki §Backend sürüm sınırı —
  1909'da kaynaklar uyarlamasız derlenmez). 1.71 UI'ı ECC üzerinde koşuyorsa varyant servisi
  başka yolla (ör. SEGW) kurulmalıdır — bu yol **DOĞRULANMADI**. Servis hiç yoksa `TablePersonalizer`
  açılışta `Log.warning` yazar ve varyantları tarayıcının `localStorage`'ında tutar (cihaza özel).
