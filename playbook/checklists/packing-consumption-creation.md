---
applies_to: [s4_private]
---
# Reviewer Checklist — Ambalajlama Talimatı Tüketimi (Packing Consumption)

> Reviewer/Bug-Expert için mekanik checklist. Ambalajlama talimatı okuyan CDS/class/FE
> işini SAP'ye yazmadan / lider'e dönmeden ÖNCE geç.
> **Kural referansı:** [`../../standards/09-packing-instruction-consumption.md`](../../standards/09-packing-instruction-consumption.md) ·
> **Reçete:** [`../howto-packing-instruction-consumption.md`](../howto-packing-instruction-consumption.md)

**Kapsam:** CDS (`ZSD001_I_ITEM_PACKING`), wrapper class (`ZCL_SD001_PACK_SRC`), FE (sip_se/ihr_se KasaAdt + detay).

---

## Checklist

| ID | Kontrol | Validator | Severity | Kural Ref |
|---|---|---|---|---|
| **PACK-01** | Talimat içeriği **released CDS** (`I_PackingInstructionHeader`/`_Component`) ile mi okunuyor? `PACKKP`/`PACKPO`'ya **ham SELECT YOK**. | manual:no-raw-packkp-select | BLOCKER | PC-1 |
| **PACK-02** | Belirleme **standart FM** `VHUPIBAPI_PACK_INST_FIND` ile mi (Tier-2 wrapper içinde)? Belirleme için kendi condition-tablo okuması YOK. | manual:fm-determination-used | BLOCKER | PC-2/PC-3 |
| **PACK-03** | Belirleme mantığı **CDS'te condition-technique yeniden-implemente edilmemiş** (erişim-sırası/coalesce hack yok)? | manual:no-cds-determination-reimpl | BLOCKER | PC-3 |
| **PACK-04** | Kademeli cascade doğru mu: ① POF-FM(MATNR+KUNWE,bugün) → ② yoksa POP `CreationDate` MAX → ③ yoksa BOŞ? | manual:cascade-order-check | BLOCKER | PC-4 |
| **PACK-05** | Kasa malzemesi **`LoadCarrierSystUUID`/MAPACO** ile mi seçiliyor? "Hedef=1"/"ilk 'P'"/malzeme-adı gibi **heuristik YOK**. | manual:crate-via-loadcarrier | BLOCKER | PC-5 |
| **PACK-06** | Kasa-içi adet = Component[`ItemCategory='I'` VE `Material=<malzeme>`].`TargetQty` mi? (Yanlış satır/`'P'` alınmamış.) | manual:incrate-qty-source | BLOCKER | PC-6 |
| **PACK-07** | Kasa sayısı = **`CEIL`** (yukarı yuvarlama), küsürat yok; kasa-içi adet 0/boş → sonuç **boş** (div-by-zero yok)? | manual:ceil-and-zero-guard | BLOCKER | PC-7 |
| **PACK-08** | Base ≠ satış birimi ise **MARM ile çevrim** var mı (CEIL'den önce)? | manual:uom-conversion-check | WARNING | PC-8 |
| **PACK-09** | Belirleme **liste/kalem yüklenince 1 KEZ** (distinct MATNR+KUNWE dedup+cache)? Miktar değişiminde **POP/POF okuması YOK** (yalnız FE CEIL)? | manual:determine-once-no-perkeystroke | BLOCKER | PC-9 |
| **PACK-10** | `POBJID` **alfanumerik-güvenli** mi? ("en son" için string-sort YOK → `CreationDate`; sayısal-değilse leading-zero strip'e dikkat.) | manual:pobjid-alphanumeric-safe | WARNING | PC-10 |
| **PACK-11** | **Display-only** — SE/belge tablosuna **yazma YOK**? | manual:read-only-check | BLOCKER | PC-11 |
| **PACK-12** | FM imzası + belirleme şeması ID'si **build'de canlı** (SE37/ADT) okundu mu — tahmin YOK? | manual:fm-signature-verified | BLOCKER | PC-2 · feedback_playbook-once-oku |
| **PACK-13** | Kendi Z objeleri naming (`ZSD001_I_*`/`ZCL_SD001_*`) + TR text; standart obje **değiştirilmemiş** (ADR 0005)? | manual:naming-and-adr0005 | BLOCKER | PC-12 |
| **PACK-14** | FE: `KasaAdt` kolonu Ağırlık'ın **soluna**, miktar `type=Text`+`onNumericLiveChange` (sayısal input kuralı, FE tuzağı); ChangeSe+CreateSe, OrderPicker HARİÇ? | manual:ui-trap-and-placement | WARNING | PC-9 · `feedback_numeric-input-no-type-number` |

> **TİP:** Her madde **HATA** (kod yanlış) veya **EKSİK** (must-do karşılanmamış) tipindedir → Bug_Expert `[HATA]`/`[EKSİK]` etiketler, ikisi de zorunlu (pass geçilmez). Checklist-dışı fikir = `[ÖNERİ]`.
>
> **Gate durumu:** Çoğu kontrol şu an **manual (reviewer yargısı)** — checklist üyeliği = enforcement. Otomasyon **follow-up (infra, onay gerekir):** `check_packing_consumption.py` (PACK-01/02/04/05/09 statik-tarama adayları) + `run_review.py --task packing_consumption` zincirleme + `skill_injector` "packing" iş-türü (T11). Bkz. `standards/09` §4.
