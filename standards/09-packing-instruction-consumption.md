---
applies_to: [s4_private]
layer: L2
scope: project-wide
type: capability-standard
applies-to: packing-instruction-consumption
version: 1.0
last-updated: 2026-07-05
status: active
source: ZSD001 SE kasa-adedi gösterimi (2026-07-05) — canlı doğrulanmış POP/POF veri modeli + released CDS + FM belirleme
---

# SAP Ambalajlama Talimatı (Packing Instruction) TÜKETİMİ — Standart

> **Bu standart neyi kapsar:** SAP LE-PAC ambalajlama talimatlarının (POP1/2/3) ve
> belirleme kayıtlarının (POF1/2/3) **SALT-OKUNUR tüketilmesini** — bir malzemenin
> hangi kasaya/ambalaja, kasa başına kaç adet konduğunu bulup uygulamada göstermeyi.
> İlk uygulama: ZSD001 SE ekranlarında "KasaAdt" (kaç kasa) gösterimi.
>
> **Operasyonel reçete + canlı kanıt** → [`../playbook/howto-packing-instruction-consumption.md`](../playbook/howto-packing-instruction-consumption.md)
> **Reviewer checklist** → [`../playbook/checklists/packing-consumption-creation.md`](../playbook/checklists/packing-consumption-creation.md)

---

## 0. NE ZAMAN BU STANDART

Bir malzemenin ambalajlama talimatını (kasa malzemesi + kasa-içi adet) okuyup uygulamada
kullanacağın HER işte. Talimat **tanımlama/değiştirme** (POP/POF yazma) bu standardın DIŞINDA —
biz yalnız **tüketiriz** (okuruz).

---

## 1. KESİN KURALLAR (force-tagged, ADR 0019)

| # | Kural | Güç |
|---|---|---|
| **PC-1** | Talimat İÇERİĞİNİ (kasa + adet) **released CDS** `I_PackingInstructionHeader` / `I_PackingInstructionComponent` ile oku (`#PUBLIC_LOCAL_API`, association-target). PACKKP/PACKPO'ya **ham SELECT YAZMA**. | **MUST-NOT** (ham SELECT) |
| **PC-2** | Talimat BELİRLEMESİNİ (malzeme[+ship-to]→talimat) **standart FM** `VHUPIBAPI_PACK_INST_FIND` (Tier-2 released wrapper class içinde) ile yap. Belirleme için released CDS/OData **YOK**. | **MUST** |
| **PC-3** | Belirleme mantığını (condition-technique: erişim-sırası + tarih-geçerliliği) **CDS'te yeniden implemente ETME** — kırılgan, anti-pattern. Yalnız FM. | **MUST-NOT** |
| **PC-4** | **Kademeli belirleme (cascade):** ① POF (FM, MATNR+KUNWE, tarih=bugün) → varsa o talimat; ② yoksa POP fallback: malzemenin **en son OLUŞTURULAN** (`CreationDate` MAX) talimatı; ③ o da yoksa **BOŞ**. | **MUST** |
| **PC-5** | **Kasa malzemesi** = header `LoadCarrierSystUUID` (MAPACO — "ana ambalaj"/yük taşıyıcı) ile eşleşen bileşenin `Material`'ı. "Hedef=1" / "ilk kalem" gibi **heuristik KULLANMA** — SAP zaten işaretliyor. | **MUST** |
| **PC-6** | **Kasa-içi adet** = talimat bileşenlerinden `PackingInstructionItemCategory = 'I'` (ürün) VE `Material = <malzeme>` olanın `PackingInstructionItmTargetQty`'si. | **MUST** |
| **PC-7** | **Kasa sayısı** = `CEIL(miktar / kasa-içi adet)` — **yukarı tam sayıya** yuvarla, küsürat YOK. Kasa-içi adet 0/boş → sonuç **boş** (bölme-hatası YOK). | **MUST** |
| **PC-8** | Kasa-içi adet **base birimde**tir (`BaseUnitofMeasure`). Tüketen miktar farklı birimdeyse **MARM (ISO/çevrim faktörü) ile base'e çevir**, sonra CEIL. | **MUST** |
| **PC-9** | **Performans:** belirlemeyi **liste/kalem yüklenirken 1 KEZ** yap (distinct `MATNR+KUNWE` dedup + cache). Miktar değişiminde **POP/POF OKUMA YOK** — yalnız FE aritmetiği (`CEIL`). Her tuş vuruşunda backend belirleme = **YASAK**. | **MUST-NOT** (per-keystroke belirleme) |
| **PC-10** | `POBJID` (talimat no) **alfanumerik olabilir** (ör. `AMB_TLMT_S1917`). Sayısal varsayma; gösterimde yalnız saf-sayısal olanların baştaki sıfırlarını at; "en son" için **string-sort değil TARİH** kullan (PC-4). | **MUST** |
| **PC-11** | Talimat belirleme = **display-only** (mevcut karar; SE/belge tablosuna YAZMA yok). Yazma gerekiyorsa ayrı karar + ADR 0005 (BAPI/RFC sırası). | **MUST** (mevcut kapsam) |
| **PC-12** | ADR 0005: standart FM **çağrısı serbest** (okuma); standart obje **değiştirme YOK**; kendi Z objelerin TR text + naming (`.rules.md`). | **MUST** |

---

## 2. VERİ MODELİ (canlı doğrulanmış — otorite)

| Katman | Nesne | Kilit alanlar |
|---|---|---|
| İçerik başlık | `I_PackingInstructionHeader` (released, packkp) | `PackingInstructionSystemUUID`(=packnr, key) · `PackingInstructionNumber`(=pobjid, "AmbTlmtNo") · **`LoadCarrierSystUUID`**(=ana kasa bileşeni) · `CreationDate` · `LastChangeDate` |
| İçerik kalem | `I_PackingInstructionComponent` (released, packpo) | `PackingInstructionSystemUUID` · `PackingInstructionItemSystUUID`(=packitemid) · **`PackingInstructionItemCategory`**('P'=ambalaj/kasa,'I'=ürün) · `Material` · **`PackingInstructionItmTargetQty`**(kasa-içi adet) · `BaseUnitofMeasure` |
| Belirleme | Condition technique (**released CDS YOK**) | `KAPPL='PO'`, `KSCHL='Z001'` · access: ①`KOTP100`(MATNR+KUNWE+tarih) ②`KOTP001`(MATNR) · `KNUMH`→`KONDP.PACKNR` · **FM `VHUPIBAPI_PACK_INST_FIND`** |

> Detay dump + FM imzası + build reçetesi: playbook howto.

---

## 3. NAMING (kendi Z objelerimiz)

Paket `.rules.md` prefix'leri geçerli: CDS `ZSD001_I_*`/`ZSD001_C_*`, wrapper class `ZCL_SD001_*`.
Kanonik öneri (build'de kesinleşir): belirleme+içerik motoru `ZCL_SD001_PACK_SRC`, tüketim view/entity
`ZSD001_I_ITEM_PACKING` (SE kalemine `_ItemPacking` olarak associate; PAK deseninin ikizi).

---

## 4. ENFORCEMENT

- **Reviewer checklist** (zorunlu, SAP-yazma öncesi): [`../playbook/checklists/packing-consumption-creation.md`](../playbook/checklists/packing-consumption-creation.md) — `PACK-01..NN`.
- **Gate-adayı (follow-up, infra — onay gerekir):** `check_packing_consumption.py` validator + `skill_injector._WORKTYPES`'e "packing" iş-türü. Şimdilik enforcement = checklist üyeliği (reviewer yargısı). Bkz. T11.
