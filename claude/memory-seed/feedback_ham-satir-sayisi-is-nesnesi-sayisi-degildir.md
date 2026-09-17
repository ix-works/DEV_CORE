---
name: feedback_ham-satir-sayisi-is-nesnesi-sayisi-degildir
description: "Ham COUNT(*) is-nesnesi sayisi degildir; teknik ayrim kolonu filtrelenmezse 2x-19x abartir (olculdu)"
metadata:
  type: feedback
---

Bir tablonun `COUNT(*)`'ı **iş nesnesi sayısı değildir**. SAP tabloları aynı fiziksel tabloda
**teknik/temsilî kayıtlar** taşır; ayırt edici kolon filtrelenmezse sayı katlarca şişer.

**İki ölçülmüş vaka (2026-09-08):**

| Tablo | Ham | Gerçek | Abartı | Ayırt edici |
|---|---|---|---|---|
| `I_EWM_HANDLINGUNITHDR` (`/SCWM/HUHDR`) | **5108** | **≈266** | **19×** | `HANDLINGUNITINDICATOR='A'` = göz/kaynak temsili **sahte HU** (4842 satır) |
| `/SCDL/DB_REFDOC` | 1886 | 994 | **2×** | her satır **iki kategoride** (`ERO`+`ERP`) ⇒ `REFDOCCAT='ERP'` şart |

*"5108 depo birimi var"* demek **19 kat** yanlış olurdu ve düppedüz bir kapasite/planlama
hükmüne götürürdü.

⚠ Aynı turda ikinci bir biçim: `A_WarehouseAvailableStock`'ta aynı `PRODUCT+BIN+QTY`
üçlüsü **8 kez** tekrarladı — kopya değil, farklı `BATCH`/`STOCKITEMUUID`.
**Parti kırılımı olmadan `SUM` alınırsa aşırı-toplama** olur.

**Why:** Ham sayı **kendinden emin** görünür ve rapora "ölçüldü" diye girer. Oysa ölçülen şey
soru DEĞİLDİR — [[feedback_kapsam-niteleyicisini-dusurme]] ve
[[feedback_satir-sayisi-artisi-cogaltma-degildir-satir-tikel-farki]] ile aynı aile.

**How to apply:**
- Bir tabloda `COUNT(*)` almadan **önce** `SELECT *` ile 3-5 satır oku ve *"bu satırların
  hepsi gerçekten benim aynı tipteki nesnem mi?"* diye sor. Tip/gösterge kolonu ara.
- Sayıyı raporlarken **filtreyi yanına yaz**: "5108 (ham) / 266 (`INDICATOR<>'A'`)". Çıplak
  sayı vermek niteleyiciyi düşürmektir.
- Ayırt edici kolonda `<>` reddedilirse (`adt_sql_query` kısıtı) `=` ile ölçüp **çıkarma**
  yap ve sonucu **"aritmetik fark"** diye nitele — doğrudan ölçüm gibi sunma.
- Tekrar eden anahtar üçlüsü görürsen **kopya sanma**; görünmeyen bir anahtar boyutu
  (parti/UUID) olabilir — `SUM` almadan önce onu bul.

İlgili: [[feedback_run-sql-query-max-rows-sessiz-kirpma]] ·
[[feedback_adt-sql-query-400-sebebi-where-terim-sayisi]] ·
[[project_ewm-embedded-erp-lgnum-cevirisi]]
