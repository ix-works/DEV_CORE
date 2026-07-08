---
applies_to: [s4_private]
---
# How-To — Ambalajlama Talimatı Tüketimi (POP/POF → kasa + kasa-içi adet)

> **L3 operasyonel reçete.** Kurallar (MUST/MUST-NOT) → [`../standards/09-packing-instruction-consumption.md`](../standards/09-packing-instruction-consumption.md).
> Reviewer → [`checklists/packing-consumption-creation.md`](checklists/packing-consumption-creation.md).
> Kanıt: <SYSTEM_ID>/100 canlı okuma (2026-07-05).

---

## 1. CANLI DOĞRULANMIŞ VERİ MODELİ

### POP — Talimat içeriği (released CDS ile oku)
- **`I_PackingInstructionHeader`** (SAP, paket `VDM_LO_HU`, `@VDM.lifecycle.contract.type: #PUBLIC_LOCAL_API` → lokal C1, association-target). Ham tablo: `PACKKP`.
  - `PackingInstructionSystemUUID` (=`packnr`, GUID key) · `PackingInstructionNumber` (=`pobjid`, "AmbTlmtNo") · **`LoadCarrierSystUUID`** (=`mapaco_item`, ana kasa bileşeni) · `CreationDate` · `LastChangeDate` · assoc `_PackingInstructionComponent`.
- **`I_PackingInstructionComponent`** (SAP, aynı contract). Ham tablo: `PACKPO`.
  - `PackingInstructionSystemUUID` · `PackingInstructionItemSystUUID` (=`packitemid`) · **`PackingInstructionItemCategory`** (`P`=ambalaj/kasa, `I`=ürün) · `Material` · **`PackingInstructionItmTargetQty`** (=`trgqty`, kasa-içi hedef adet) · `BaseUnitofMeasure`.

### POF — Belirleme (released CDS/OData YOK → FM şart)
- Condition technique: `KAPPL='PO'`, `KSCHL='Z001'` (kullanıcının "Z001-TDF"si).
  - Erişim ①: **`KOTP100`** — `MATNR + KUNWE` (ship-to; **KUNAG değil**) + `DATAB/DATBI` geçerlilik → `KNUMH`.
  - Erişim ②: **`KOTP001`** — `MATNR` → `KNUMH`. (**WERKS/plant yok.**)
  - `KNUMH` → **`KONDP`**.`PACKNR` (+ `PACKNR1..4` alternatif kademeler).
- **FM `VHUPIBAPI_PACK_INST_FIND`** (FUGR VHUPIBAPI) — `I_KOMGP`(MATNR/KUNWE) + tarih + şema → `E_KONDP`(içinde `PACKNR`). Çekirdek motor: `VHUPOSEL_PACK_INST_DETERMINE`.
  - ⚠️ Tam import/export imzasını **build'de SE37/ADT'den canlı oku** (MCP `func`-okuma standart FM'de sınırlı; TAHMİN YASAK). Belirleme şeması ID'sini customizing'den (POF3/T682) al.

### Canlı örnek (4 talimat — sistemde bunlar var)
| POBJID (AmbTlmtNo) | Ana kasa (MAPACO→'P') | Yardımcı 'P' | Ürün 'I' | Kasa-içi |
|---|---|---|---|---|
| `00000000000000000002` | KASA0007 | 40000148 | S1166 | 100 |
| `00000000000000000003` | KASA0007 | 40000148 | S1917 | 100 |
| `00000000000000000005` | KASA0007 | 40000148 | S1119 | 25 |
| **`AMB_TLMT_S1917`** | KASA0007 | 40000148 | S1917 | 40 |

Belirleme: S1917+KUNWE 600003 → `AMB_TLMT_S1917` (40); S1917 genel (KOTP001) → talimat 3 (100). Aynı malzeme, ship-to'ya göre farklı kasa-içi adet → erişim sırası şart.

---

## 2. UÇTAN-UCA OKUMA YOLU

```
(MATNR, KUNWE=ship-to, tarih=bugün)
 ① VHUPIBAPI_PACK_INST_FIND → PACKNR ?
      ✔ → içerik (aşağı)
      ✘ → ② POP fallback: I_PackingInstructionComponent[ItemCategory='I', Material=MATNR]
              → _Header'lardan CreationDate MAX olanı seç → PACKNR
      ✘✘ → BOŞ (kasa yok)
 İçerik (PACKNR ile, released CDS):
   kasa-içi adet = Component[ItemCategory='I', Material=MATNR].PackingInstructionItmTargetQty
   kasa malzeme = Component[ItemSystUUID = Header.LoadCarrierSystUUID].Material   (= KASA0007)
   kasa mlz adı = kasa malzemenin metni (MAKT / released ürün-text CDS)
   birim        = BaseUnitofMeasure
 Tüketen:
   kasa sayısı = CEIL( çevrilmiş_miktar / kasa-içi adet )   [MARM base'e çevir]
```

---

## 3. BUILD REÇETESİ (öneri — build-design'da kesinleşir)

1. **Tier-2 wrapper class** `ZCL_SD001_PACK_SRC` (released interface): metot `get_packing( matnr, kunwe, date ) → { pobjid, crate_mat, crate_name, in_crate_qty, base_uom, source(POF/POP) }`.
   - İçeride: FM çağır → boşsa released CDS fallback (CreationDate MAX). Distinct-key **internal-table cache** (N+1 önle).
2. **Tüketim view/entity** `ZSD001_I_ITEM_PACKING` → SE kalemine `_ItemPacking` association (PAK deseni; ABAP-destekli çünkü FM). Alanlar: kasa malzeme, kasa adı, kasa-içi adet, AmbTlmtNo.
3. **Expose:** GetOpenQty deseni — function import VEYA custom-entity, IHRSE/SIPSE servisinde. Belirleme **liste yüklenince 1 kez**.
4. **FE (sip_se + ihr_se):** kalem tablosuna `KasaAdt` kolonu (Ağırlık'ın soluna) = `CEIL(SevkMiktarı / kasa-içi adet)` canlı; kalem-detay "Ambalajlama Talimatı" başlığı: AmbTlmtNo / Kasa Malzemesi / Kasa Mlz Adı / Kasa İçi Adet. ChangeSe + CreateSe. OrderPicker'a EKLENMEZ.

---

## 4. TUZAKLAR (acı çekmeden önce oku)

- **T1 — Belirleme CDS'te taklit edilmez:** erişim-sırası önceliği + tarih-geçerliliği + PACKNR1-4 kademesi. FM şart (PC-3).
- **T2 — Kasa ≠ ilk 'P':** her talimatta 2+ 'P' (kasa + ara-ayraç `40000148`) olabilir. Kasa = `LoadCarrierSystUUID`/MAPACO (PC-5). Heuristik yanlış kasa verir.
- **T3 — POBJID alfanumerik:** `AMB_TLMT_S1917` gerçek POBJID. Sayısal varsayma; "en son"u string-sort ETME → `CreationDate` (PC-4/PC-10).
- **T4 — Birim:** `TargetQty` base UoM'da. SE satış birimi farklıysa MARM çevir, sonra CEIL (PC-8).
- **T5 — Per-keystroke belirleme YASAK:** belirle-bir-kez + FE `CEIL`. Miktar değişimi backend'e gitmez (PC-9).
- **T6 — FM imzası:** standart FM imzasını build'de canlı oku (SE37/ADT), tahmin etme. Belirleme şeması ID'si customizing'den.
- **T7 — Released CDS varlığı sistem-bağımlı:** bu sistemde `I_PackingInstruction*` released VAR (2022 FPS). Genel web "yok" diyebilir — canlı `adt_get` ile teyit et (feedback_ajan-olumsuz-donusu / clean-core).
