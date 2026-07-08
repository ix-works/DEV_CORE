---
applies_to: [s4_private]
layer: L3
type: playbook
module: SD
scope: project-wide
status: active
purpose: ITG modül kural-paketi (SD) — tetik-haritası + kontrol + soru + ders (bilgi-deposu DEĞİL)
---

# SD Modül Kural-Paketi — Intake Triage için (ADR 0022)

> **Ne bu:** SD (Satış-Dağıtım) işi geldiğinde ITG protokolünün (`../intake-triage.md`) adım-2'de
> okuduğu **tetik-haritası + kontrol-listesi + soru-şablonu + kaynak-işaretçisi**.
> **Ne DEĞİL:** SD bilgi-deposu. Domain-olgusunu ezber sanma; bu paket ajanı doğru kaynağa
> (canlı sistem + docs-MCP + prior-art) YÖNLENDİRİR. Uzmanlık kaynak-zincirinden çıkar (persona-placebo, ADR 0022).
> **Nasıl büyür:** yeni SD tuzağı/dersi öğrenilince T-trigger + gün-sonu terfi ile satır eklenir.

---

## ZORUNLU KONTROL (SD işi + kapsam ≥ S1)

| # | Kontrol | Kural |
|---|---|---|
| SD-K1 | **Std objeleri where-used + CANLI oku, VARSAYMA** — VBAK/VBAP (sipariş), VBEP (termin), VBFA (doc-flow), LIKP/LIPS (teslimat), VBRK/VBRP (fatura), KONV/PRCD_ELEMENTS (pricing), VTTK/VTTS (nakliye), VFKP (navlun) | TAHMİN YASAK (hafıza=hipotez, canlı=otorite; ADR 0016) |
| SD-K2 | **Akış-eksenini belirle** — sipariş → teslimat → fatura hangisinde? (copy-control/doc-flow etkisi) | model bütünlüğü |
| SD-K3 | **Std belge YAZMA** — LIKP/VTTK/VBRK/VBAK'a direkt yazım YASAK → released-API → BAPI → BDC sırası (BAPI_OUTB_DELIVERY_CREATE_SLS, BAPI_SHIPMENT_CREATE, SD_SCDS_CREATE). Z katman icra belgesi yazmaz, **doğru belirleyicilerle besler** | ⛔ ADR 0005 A/B · ADR 0015 |
| SD-K4 | **Müşteri/BP verisi released CDS'ten** — ham KNA1/KNVV/BUT000 YASAK → I_Customer / I_CustomerSalesArea / I_BusinessPartner / I_Supplier | ⛔ ADR 0005 A · clean-core |
| SD-K5 | **Commit'li BAPI ayrı LUW** — SD belgesi yaratan commit'li FM (BAPI_SHIPMENT_CREATE, SD_SCDS_CREATE `i_opt_commit`) RAP handler'dan DİREKT çağrılamaz → RFC-FM ayrı LUW | [[bug-checklist-backend]] BE-26 |

---

## TETİK-HARİTASI (ister/alan → domain-konu → araştır + mevcut-sistemde-bak + tuzak)

> Her anlamlı istek/alan bir domain-konusu tetikler. Konuyu **3-eksen araştır** (domain + canlı-sistem + prior-art),
> SONRA değerlendir/sor. Aşağıdaki tetikler örnek-katalog; talebe göre yenisini de türet.

### T-SD-1 · "kullanılabilir stok / depo stoğu / ATP" → STOK + AVAILABILITY
- **ARAŞTIR:** EWM mi IM/MM mi? (embedded EWM prodüktif olabilir — LENVW='E' → EWM). Kaynak:
  EWM=`A_WarehouseAvailableStock` (lgnum-keyli; plant/lgort YOK → lgnum↔lgort ters-eşleme), MM=`I_MaterialStock`
  (InventoryStockType='01', SDDocument=''). ⚠ `I_MaterialStock` deprecated olabilir → successor/analitik-cube DEV-teyit.
- **MEVCUT-SİSTEMDE-BAK:** aggregate-view üçlüsü deseni (STOCK_BY_LOC + DISPATCHED_BY_LOC + DELIVERED_BY_LOC,
  Material+Plant+StorageLocation) + boş-depo (lgort='') → Plant-toplam fallback. Böyle view'lar VARSA **reuse et**, yeni yazma.
- **FORMÜL DERSİ (kritik):** `Kullanılabilir = Stok − (SE-tahsis − MÇyapılan-teslimat)`. Naif `Stok − Dispatched`
  GI-sonrası stoğu OLDUĞUNDAN AZ gösterir (bug) → teslimatı geri-ekleyen 3. terim ŞART.
- **TUZAK:** [[bug-checklist-backend]] BE-44 (set-based SUM implicit-DISTINCT under-count) · BE-45 (item-view assoc-türevli join-key → SDDL 515/061).
- **SORU:** özel-stok E (SDDocument≠'') dahil mi hariç mi? Plant mı Plant+Lgort mu? (pool-semantik çift-sayım riski).

### T-SD-2 · "tutar / fiyat / döviz / bakiye" → PRICING + CURRENCY
- **ARAŞTIR:** çok-para-birimli mi? Kur tipi parametreli mi? CDS `currency_conversion(p_kur_tipi)`.
- **MEVCUT-SİSTEMDE-BAK:** 3-katman analitik CDS + currency_conversion deseni varsa reuse.
- **TUZAK:** `currency_conversion error_handling=>#SET_TO_NULL` bazı derleyicide YOK → **TCURR rate bakımı operasyonel ön-koşul**
  (yoksa runtime dump) · [[bug-checklist-backend]] BE-32 (UNIT/CUKY kolonu max/min/sum reddi → GROUP BY) · BE-04 / [[bug-checklist-frontend]] FE-28 (decimal `WRITE...TO` API body → Edm.Decimal 400).
- **SORU:** hangi kur tipi? Bazı belge-tiplerinde (parça-sipariş/ihracat) FİYAT YOK → ORDERPRICE kullanma; bakiye = OrderQty − Σdispatch.

### T-SD-3 · "teslimat / mal çıkışı (GI) / sevkiyat" → DELIVERY
- **ARAŞTIR:** SE-kaynaklı teslimat ayracı (ZZ1 append alanı `<0>`≠) + GI durumu `LIPS.wbsta='C'`; teslimat NET = fwd − iade.
- **MEVCUT-SİSTEMDE-BAK:** tip-agnostik shipment havuzu + DELIVERY_API façade varsa reuse; CreateDelivery released-API→BAPI.
- **TUZAK:** teslimat parti-BOŞ çalışır (SAP determine — güvenli) · std save-exit (MV50AFZZ) yalnız Z include (ADR 0005-A) ·
  `MARM` alternatif UoM (ST↔PAK) eksikse teslimat OLUŞMAZ (test ön-koşulu).
- **DORMANT uyarısı:** canlıda SE-bağlı teslimat yoksa DeliveredQty=0 → guard dormant; spekülatif-blocker YAPMA, veri gelince aktive.

### T-SD-4 · "ambalajlama / kasa / paketleme adedi" → PACKING (LE-PAC)
- **ARAŞTIR:** ambalajlama talimatı içerik vs belirleme; condition-technique. İçerik=released `I_PackingInstructionHeader/_Component`; belirleme=FM `VHUPIBAPI_PACK_INST_FIND` (KAPPL=PO).
- **MEVCUT-SİSTEMDE-BAK:** hibrit belirleme (FM→CreationDate MAX→boş) + belirle-BİR-KEZ (liste-yükte dedup+cache) deseni varsa reuse.
- **TUZAK:** condition-technique'i CDS'te TAKLİT ETME (kırılgan) → FM · SalesUnit≠BaseUom → kasa boş (MARM çevrimi) · [[bug-checklist-frontend]] FE-35 (miktar düz-concat QUAN trailing-zero "14.000 ADT" → birim-ondalık formatter).

### T-SD-5 · "termin / açık miktar / sipariş bakiyesi" → SCHEDULING
- **ARAŞTIR:** SA schedule-line (`I_SalesSchedgAgrmtSchedLine`), ETTYP filtresi (firm-only?), FIFO consume MBDAT≤bugün+N.
- **MEVCUT-SİSTEMDE-BAK:** açık-miktar motoru (`açık = max(0, OrderQty − delivered − ΣSE_açık)`) + RAP façade fn-import varsa reuse; motor tip-param'lı olmalı (hard-code ETME).
- **TUZAK:** over-delivery toleransı → cap = termin×(1+UEBTO%) · [[bug-checklist-backend]] BE-29 (açık-miktar COLLECT hedefinde non-key CHAR → aktivasyon reddi) · 30-gün mükerrer-parti elemesi tip-spesifik (global varsayma).

### T-SD-6 · "konteyner / kapasite / brüt ağırlık" → KAPASİTE
- **ARAŞTIR:** konteyner tipi std VTADD02'de → kapasite oraya KONAMAZ (ADR 0005) → Z tabloya senkron.
- **MEVCUT-SİSTEMDE-BAK:** Z kapasite tablosu + Σ teslimat brüt (`LIKP.BTGEW`) GROUP BY (gewei) kıyas + soft-uyarı deseni varsa reuse.
- **TUZAK:** [[bug-checklist-backend]] BE-32 (`max(gewei)` UNIT aggregate reddi → GROUP BY) · **blast-radius:** kapasite alanı ekleme = cross-package where-used ŞART (netgew/volum tüketicisi).

### T-SD-7 · "müşteri blok / kredi / teslimat bloğu" → PARTNER-BLOCK
- **ARAŞTIR:** blok bayrakları BUT000-XBLCK + KNA1/KNVV-AUFSD + LIFSD; muhataplar AG/WE/RE/RG distinct.
- **MEVCUT-SİSTEMDE-BAK:** reusable partner-block-check (I_Customer/I_CustomerSalesArea/I_BusinessPartner) varsa reuse; ham tablo YASAK.
- **TUZAK:** **KNVV blokları division-keyli** → çağıran spart'ı beslemezse AUFSD/LIFSD SESSİZCE atlanır (division=vbak.spart ZORUNLU) · [[bug-checklist-backend]] BE-19 (BU_PARTNER≠KUNNR CVI → generic BP-name join boş/yanlış; KUNNR→I_Customer).

---

## SORULACAK (belirsizse DUR — belirsizlik-kalibreli; makul-default'ta varsay-bildir)
1. **Satış org / kanal / bölüm (vkorg/vtweg/spart) + belge tipi (auart) kırılımı?** — config-key buna bağlı; iki akış aynı vkorg+vtweg+auart'ı paylaşıp yalnız **SPART**'la ayrışabilir (config-overlap tuzağı, BE-43).
2. **Özel stok E dahil mi hariç mi?** — availability formülünü değiştirir.
3. **Stok kırılımı Plant mı Plant+StorageLocation mı? Boş-depo davranışı?**
4. **EWM mi IM/MM mi (depo-yeri bazlı)?** — stok CDS kaynağını belirler.
5. **Bakiye/açık-miktar teslimat-bazlı mı sipariş-bazlı mı?** — CDS-teyitli al.
6. **Over-delivery toleransı (UEBTO) cap'e dahil mi?**
7. **Fiyat/tutar var mı (SO vs SA vs ihracat)?** — yoksa ORDERPRICE kullanma.
8. **Çok-para-birimli mi + hangi kur tipi?** — TCURR bakım ön-koşulu.
9. **Blok kontrol hangi muhataplar + hangi kapılar (yaratma / teslimat)?**
10. **Değiştirmede kendi-hariç-tut mantığı?** — bakiye/kapasitede düzenlenen belge kendisi hariç mi.

---

## KAYNAK-İŞARETÇİSİ (3-eksen araştırmada nereye bak)
- **Domain/syntax/annotation** → docs-MCP (resmi ABAP/CDS referansı; tahmin-kesici) + released-API tarama
- **Canlı sistem** → `adt_where_used` + `adt_package_contents` (harita) → `adt_get` (derin) + `adt_table_read`
- **Proje kuralı/istisna** → paket `<source_root>/SD/<PKG>/.rules.md`
- **Benzer çözülmüş iş (prior-art)** → paket `SESSION_NOTES.md` + `playbook/lessons-learned.md` + memory (Z-obje ise CANLI DOĞRULA)
- **Teknik-tip (RAP/klasik/Fiori)** → skill_injector'ın enjekte ettiği obje-tipi checklist'i (dik eksen)

---

## ÇIKARILAN DERSLER (SD-özgü; T-trigger ile büyür)
Yukarıdaki tetiklere gömülü tuzaklar + [[bug-checklist-backend]] (BE-19/26/29/32/43/44/45/46/04) ve
[[bug-checklist-frontend]] (FE-27/28/35) SD-domain maddeleri. Yeni SD dersi öğrenilince **buraya satır ekle**
(gün-sonu terfi). Std belge yazımı daima released-API→BAPI→BDC (ADR 0015); RAP handler'da commit'li BAPI ayrı LUW (BE-26).
