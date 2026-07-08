# 0013 — Kaynak/Referans Doküman Ayrımı: `ref_docs/`

**Durum:** Kabul edildi (2026-06-09)
**Bağlam ADR'leri:** [0003](0003-layered-rule-architecture.md) (katman mimarisi), [0004](0004-erp-modul-bazli-organizasyon.md) (paket organizasyonu)
**Pilot:** ZSD001_CLC (commit `7621cadb`)

---

## Bağlam

Bir Z paketi sıklıkla **başka bir sistemden** (eski <LEGACY_SOURCE>, başka SAP sistemi, legacy)
alınan kod/spec'in **S4 DEV'de yeniden yazılmasıyla** doğar. Bu dönüşüm sürecinde paket
köküne çok sayıda **conversion/planlama dokümanı** birikir: klasik DDL/struct spec'leri,
program FS+TS conversion docs, ekran mockup'ları, çıkarılmış obje listeleri (csv),
conversion-dönemi genel-bakış/FS/farklılık docs.

Bunların çoğu **S4'te 1:1 yaratılmaz** (ör. klasik DDL → RAP view entity ile yeniden kurulur).
Paket kökünde **gerçek S4 artefaktlarıyla karışınca** kafa karışıklığı yaratırlar: hangi dosya
canlı teslimat, hangisi sadece dönüşüm referansı belli olmaz.

## Karar

Her pakette **`ref_docs/`** klasörü = **kaynak/dönüşüm + tarihsel referans** malzemesi.

- **`ref_docs/` içine:** Başka sistemden alınıp S4'te **1:1 yaratılmayacak** her şey —
  klasik DDL/struct spec'leri, conversion program spec'leri, ekran mockup'ları, çıkarım csv'leri,
  conversion-dönemi planlama docs (FS/farklılık/bağımlılık/genel-bakış), superseded/tarihsel docs.
  Bunlar **build sırasında spec kaynağıdır**, canlı teslimat değildir.
- **Paket kökü:** Yalnızca **gerçek S4 DEV artefaktları** (yaratılan CDS/RAP/class/UI kaynak
  aynaları) + **yaşayan governance/plan docs** (SPRINT_PLAN, SESSION_NOTES, SPEC, .rules.md, overview).
- **Çok-kaynak:** Birden çok kaynak sistemden malzeme gelirse `ref_docs/<kaynak>/` alt klasörü
  (ör. `ref_docs/<legacy_source>/`). Tek kaynakta düz `ref_docs/`.
- **Manifest:** `ref_docs/README.md` zorunlu — provenance (hangi sistem, orijinal obje) +
  **durum** (ham / superseded→gerçek obje / düştü).
- **Yaşam döngüsü:** Gerçek S4 objesi + dokümanı oluşunca ilgili referans manifest'te
  "superseded" işaretlenir. Nihai temizlik = ilgili "ölü-set süpürmesi" sprint'i (where-used temiz).
- **`ref_docs/` "temp/çöp" DEĞİL:** Spec kaynağı olduğu için tüketilene kadar **silinmez**.

## Gerekçe

- **"Safety/clarity is structure, not memory":** Ne canlı ne referans — agent'ın hatırlamasına
  bırakılmaz; klasör konumu söyler.
- Kök tarama (build, review, yeni geliştirici) yalnızca **güncel** artefaktları görür.
- Provenance + durum manifesti, "bu klasik DDL'i 1:1 mi yaratacağım?" sorusunu kökten kaldırır.

## Sonuçlar

- `bootstrap_package.py` / `templates/new-package/`: yeni paketler `ref_docs/` + manifest şablonu
  ile gelir.
- `standards/04-documentation-fs-ts.md`: konvansiyon belgelenir.
- `sap-abap-dev` skill: build adımı "spec kaynağı `<PKG>/ref_docs/`'te" pointer'ı.
- Link disiplini: kök↔`ref_docs/` arası göreli yollar (`../`), `ref_docs/` içi sibling.
  Tarihsel log satırları (geçmiş kayıt) yeniden yazılmaz.
- T12: konvansiyon DEVELOPMENT_TEMPLATE_FILES'a port edilir (saf altyapı).
