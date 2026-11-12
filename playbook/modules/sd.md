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
| SD-K3 | **Std belge YAZMA** — LIKP/VTTK/VBRK/VBAK'a direkt yazım YASAK → released-API → BAPI → RFC FM → BDC sırası — genel karar ağacı [`standards/10`](../../standards/10-standart-veriye-yazma-api-secimi.md); SD örnekleri: BAPI_OUTB_DELIVERY_CREATE_SLS, BAPI_SHIPMENT_CREATE (BAPI) · SD_SCDS_CREATE (resmi FM, RFC-enabled DEĞİL → std/10 ADIM 4; RAP handler'dan Z RFC sarmalayıcıyla). Z katman icra belgesi yazmaz, **doğru belirleyicilerle besler** | ⛔ ADR 0005 A/B · ADR 0015 |
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
- ⚠ **Embedded EWM:** ERP ambar no ≠ EWM ambar no — çevirmeden sorgu sessizce 0 satır (aşağıda **SD-D1**); müşteri konsinyesinde depo yeri boyutu yok (**SD-D9**).

### T-SD-2 · "tutar / fiyat / döviz / bakiye" → PRICING + CURRENCY
- **ARAŞTIR:** çok-para-birimli mi? Kur tipi parametreli mi? CDS `currency_conversion(p_kur_tipi)`.
- **MEVCUT-SİSTEMDE-BAK:** 3-katman analitik CDS + currency_conversion deseni varsa reuse.
- **TUZAK:** `currency_conversion error_handling=>#SET_TO_NULL` bazı derleyicide YOK → **TCURR rate bakımı operasyonel ön-koşul**
  (yoksa runtime dump) · [[bug-checklist-backend]] BE-32 (UNIT/CUKY kolonu max/min/sum reddi → GROUP BY) · BE-04 / [[bug-checklist-frontend]] FE-28 (decimal `WRITE...TO` API body → Edm.Decimal 400).
- **Fiyat onayı / koşul kaydı yazma:** standart onay `KFRST`'siz koşul tablosunda çalışmaz; released yazma API'si (aşağıda **SD-D10**).
- **SORU:** hangi kur tipi? Bazı belge-tiplerinde (parça-sipariş/ihracat) FİYAT YOK → ORDERPRICE kullanma; bakiye = OrderQty − Σdispatch.

### T-SD-3 · "teslimat / mal çıkışı (GI) / sevkiyat" → DELIVERY
- **ARAŞTIR:** SE-kaynaklı teslimat ayracı (ZZ1 append alanı `<0>`≠) + GI durumu `LIPS.wbsta='C'`; teslimat NET = fwd − iade.
- **MEVCUT-SİSTEMDE-BAK:** tip-agnostik shipment havuzu + DELIVERY_API façade varsa reuse; CreateDelivery released-API→BAPI.
- **TUZAK:** teslimat parti-BOŞ çalışır (SAP determine — güvenli) · std save-exit (MV50AFZZ) yalnız Z include (ADR 0005-A) ·
  `MARM` alternatif UoM (ST↔PAK) eksikse teslimat OLUŞMAZ (test ön-koşulu).
- ⚠ **Embedded EWM:** "dağıtıldı" ≠ EWM kabul etti, qRFC iki yönde de SMQ2'de (aşağıda **SD-D2**) · e-irsaliye eklentisi teslimat silmede popup → BAPI ile silme kırılır (**SD-D3**).
- **DORMANT uyarısı:** canlıda SE-bağlı teslimat yoksa DeliveredQty=0 → guard dormant; spekülatif-blocker YAPMA, veri gelince aktive.

### T-SD-4 · "ambalajlama / kasa / paketleme adedi" → PACKING (LE-PAC)
- **ARAŞTIR:** ambalajlama talimatı içerik vs belirleme; condition-technique. İçerik=released `I_PackingInstructionHeader/_Component`; belirleme=FM `VHUPIBAPI_PACK_INST_FIND` (KAPPL=PO).
- **MEVCUT-SİSTEMDE-BAK:** hibrit belirleme (FM→CreationDate MAX→boş) + belirle-BİR-KEZ (liste-yükte dedup+cache) deseni varsa reuse.
- **TUZAK:** condition-technique'i CDS'te TAKLİT ETME (kırılgan) → FM · SalesUnit≠BaseUom → kasa boş (MARM çevrimi) · [[bug-checklist-frontend]] FE-35 (miktar düz-concat QUAN trailing-zero "14.000 ADT" → birim-ondalık formatter).

### T-SD-5 · "termin / açık miktar / sipariş bakiyesi" → SCHEDULING
- **ARAŞTIR:** SA schedule-line (`I_SalesSchedgAgrmtSchedLine`), ETTYP filtresi (firm-only?), FIFO consume MBDAT≤bugün+N.
- **MEVCUT-SİSTEMDE-BAK:** açık-miktar motoru (`açık = max(0, OrderQty − delivered − ΣSE_açık)`) + RAP façade fn-import varsa reuse; motor tip-param'lı olmalı (hard-code ETME).
- **TUZAK:** over-delivery toleransı → cap = termin×(1+UEBTO%) · [[bug-checklist-backend]] BE-29 (açık-miktar COLLECT hedefinde non-key CHAR → aktivasyon reddi) · 30-gün mükerrer-parti elemesi tip-spesifik (global varsayma).
- ⚠ **Teslimat planı (SA):** VBEP açık miktar için güvenilmez, havuz `S073 − VBLB-ABEFZ` (aşağıda **SD-D7**) · çağrı geçmişi okuma tuzakları (**SD-D8**).

### T-SD-6 · "konteyner / kapasite / brüt ağırlık" → KAPASİTE
- **ARAŞTIR:** konteyner tipi std VTADD02'de → kapasite oraya KONAMAZ (ADR 0005) → Z tabloya senkron.
- **MEVCUT-SİSTEMDE-BAK:** Z kapasite tablosu + Σ teslimat brüt (`LIKP.BTGEW`) GROUP BY (gewei) kıyas + soft-uyarı deseni varsa reuse.
- **TUZAK:** [[bug-checklist-backend]] BE-32 (`max(gewei)` UNIT aggregate reddi → GROUP BY) · **blast-radius:** kapasite alanı ekleme = cross-package where-used ŞART (netgew/volum tüketicisi).

### T-SD-7 · "müşteri blok / kredi / teslimat bloğu" → PARTNER-BLOCK
- **ARAŞTIR:** blok bayrakları BUT000-XBLCK + KNA1/KNVV-AUFSD + LIFSD; muhataplar AG/WE/RE/RG distinct.
- **MEVCUT-SİSTEMDE-BAK:** reusable partner-block-check (I_Customer/I_CustomerSalesArea/I_BusinessPartner) varsa reuse; ham tablo YASAK.
- **TUZAK:** **KNVV blokları division-keyli** → çağıran spart'ı beslemezse AUFSD/LIFSD SESSİZCE atlanır (division=vbak.spart ZORUNLU) · [[bug-checklist-backend]] BE-19 (BU_PARTNER≠KUNNR CVI → generic BP-name join boş/yanlış; KUNNR→I_Customer).

### T-SD-8 · "karakteristik değeri / konfigürasyon / varyant" → VARYANT KONFİGÜRASYONU
- **ARAŞTIR:** motor tipi önce (`CUCO-PROC_MODE` boş = klasik, `A` = AVC); belge değeri okuma zinciri, released durumu, değer değiştirme yolu: [`../howto-lovc-belge-konfigurasyonu-okuma-yazma.md`](../howto-lovc-belge-konfigurasyonu-okuma-yazma.md).
- **MEVCUT-SİSTEMDE-BAK:** model hangi client'ta kurulu (geliştirme client'ında iskelet olabilir); profile bağlı Z varyant fonksiyonları (kullanıcıya bağlı sonuç); mevcut `VC_I_GET_CONFIGURATION` kullanan programlar.
- **TUZAK:** belge değerlerini okuyan released CDS YOK · `…Basic` view'lar released DEĞİL · BAPI ile değişiklikte POSEX boş/eşleşmez = SESSİZ ATLAMA, yalnız değişeni göndermek diğerlerini siler, türetilmişi göndermek dondurur · iç numaralar (ATINN/CUOBJ) client'a özel. Kalemi konfigürasyonuyla devretme ayrı konu: [`../howto-sd-karakteristik-hizli-giris.md`](../howto-sd-karakteristik-hizli-giris.md).

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

> **Terfi notu (2026-11-12, kuyruk Q407 D):** aşağıdaki SD-D1…D11, bir tüketici projenin hafızasında
> "proje hatırası" olarak duran ama **standart SAP davranışı** olan bilgilerdir; proje izi (sistem,
> ambar/tesis kodu, belge no, müşteri) ayıklanarak buraya taşındı. Hepsi **tek bir S/4 private
> DEV sisteminde ölçüldü** — başka sistemde **hipotezdir**, kullanmadan önce canlıda doğrula
> (üstteki "Ne DEĞİL" notu). Sessiz hata üretenler ⚠ ile işaretli.

### SD-D1 ⚠ Embedded EWM: ERP ambar no ≠ EWM ambar no (stok sorgusu sessizce 0 satır) — T-SD-1
- Embedded EWM'de (ERP ile aynı istemci; `/SCWM/T300` dolu, `I_EWM_PLANTSTORLOCMAPTOWHSE.ERPLOGICALSYSTEM`
  kendi mantıksal sistemi) ERP `LGNUM` (3 karakter) ile EWM `LGNUM` (4 karakter) **farklı kodlardır**.
- `LIKP-LGNUM` **ERP** kodunu taşır; `/SCWM/*` ve `A_WarehouseAvailableStock` **EWM** kodunu ister.
  Çeviri **`I_EWM_PLANTSTORLOCMAPTOWHSE`** (plant + depo yeri → EWM ambarı); `T320` tek başına yetmez (yalnız ERP LGNUM).
- Çeviri atlanırsa sorgu **hata vermez, 0 satır döner** (PATTERN #32 sınıfı) → "EWM'de stok yok" yanlış hükmü.
- Yardımcılar: `A_WarehouseAvailableStock.PRODUCT` = gerçek MATNR (GUID eşlemesi gerekmez) · `BATCH` = `LIPS-CHARG` ·
  ERP teslimat ↔ EWM belge köprüsü `/SCDL/DB_REFDOC` (`REFDOCCAT='ERP'`, `DOCCAT='PDO'`) ya da released
  `I_EWM_DELIVERYREFERENCEDOC` · klasik WM kullanılmıyorsa `LIKP-LVSTK` boştur, anlamlı olan `LIKP-VLSTK` (EWM dağıtım durumu).
- ⚠ Depo görevi belge anında henüz yoktur ⇒ göz bilgisi o anda **tahsis değil, bulunabilirliktir**.

### SD-D2 ⚠ Embedded EWM qRFC: iki yön de SMQ2'de; "dağıtıldı" ≠ EWM kabul etti — T-SD-3
- ERP→EWM ve EWM→ERP kuyruk kayıtlarının **ikisi de gelen kuyrukta (SMQ2 / `TRFCQIN`)**; SMQ1'de (`TRFCQOUT`) EWM kaydı
  beklenmez (oradaki `MCEX_UPDATE_*` kayıtları LO veri çıkarımıdır). Kullanıcı "SMQ1'de bekliyor" dese de **SMQ2'de ara**.
- Yön kuyruk adı önekinden değil **fonksiyon adından (`QRFCFNAM`)** okunur: `DLVS…` = `/SCWM/OUTB_DLV_SAVEREPLICA`
  (ERP→EWM, ODO kopyası) · `DLWS…` = `BAPI_OUTB_DELIVERY_CHANGE` / `…_CONFIRM_DEC` (EWM→ERP) · `WMDPPDO…` = `/SCWM/PPF_POST_GM` ·
  `EWMSGM_<LGNUM>…` = `/SPE/GOODSMVT_CREATE`. Hedef (`DEST`) bir uygulama sunucusu adı taşıyabilir — "ayrı sistem" belirtisi DEĞİL.
- Kuyruk FIFO'dur: baştaki SYSFAIL arkasındaki aynı adlı LUW'leri kilitler. İşlenen LUW silinir ⇒ "kuyrukta 0 satır"
  zaman bilgisi taşımaz (henüz gelmedi / işlendi ayırt edilemez).
- ⚠ Teslimat `VLSTK` ile "dağıtıldı" görünürken EWM kopyayı reddetmiş olabilir (SYSFAIL; ör. EWM'de kalem türü
  uyarlaması eksik) ⇒ ODO **asenkron** doğar ya da hiç doğmaz; bekleme/poll kalıcı yokluğu çözmez.
- Tasarım: birincil kapı released CDS (`I_EWM_OutbDelivOrdHdr`); `TRFCQIN` released değil (ham Basis tablosu) — en fazla
  best-effort teşhis. Teşhis: `SELECT qname, qstate, qrfcfnam, qrfcdatum, errmess FROM trfcqin WHERE qname LIKE '%<teslimat>%'`
  (`TRFCQOUT`'ta `qrfcfnam` kolonu 500 verdi — çıkar). Kuyruk işlemleri (yeniden çalıştır/sil) operasyonun işidir, AI yapmaz.

### SD-D3 ⚠ Üçüncü parti e-irsaliye BAdI'si teslimat silmede popup açar → BAPI/RFC ile silme kırılır — T-SD-3
- Türkiye e-dönüşüm eklentisi kurulu sistemde (ör. `/ITETR/` partner ad alanı) `LE_SHP_DELIVERY_PROC~DELIVERY_DELETION`
  uygulaması, teslimatın e-irsaliye kaydı varsa `POPUP_TO_CONFIRM` açar. Metin T100'de değil **metin sembolünde** —
  mesaj aramasında çıkmaz.
- RFC/OData oturumunda `CX_SY_SEND_DYNPRO_NO_RECEIVER` (SAPLSPO1 0500); cevap '1' değilse `MESSAGE a…` oturumu keser.
  `sy-batch` RFC/OData'da **boştur** ⇒ "BAPI'den mi geldi" ayrımında işe yaramaz; doğru ayraç `GUI_IS_AVAILABLE` (FUGR SFES, released).
- Partner ad alanı ADR 0005-A kapsamındadır — dokunulmaz; düzeltmeyi eklentinin sahibi yapar. Program içinden teslimat
  silme/değiştirme "dynpro no receiver" ile düşerse önce bu BAdI'ye bak; geçici yol VL02N'den manuel silme.

### SD-D4 SD GOS kalem bazında ek TUTMAZ — kalem için DMS bağlantısı ya da Z geliştirme
- `CL_SD_SLS_GOS` → `SD_OBJECT_TYPE_DETERMINE` kalem nesnesini (VBAP) de döndürür ama `gos_publish_object` yalnız başlık
  BOR'unu (BUS2031/BUS2032) `CL_GOS_MANAGER`'a verir; `SRGBTBREL-INSTID_A` = VBELN. Uyarlama anahtarı **yok**.
- Kalem BOR'u var (TOJTB `VBAP` "SalesItem", anahtar VBELN+POSNR). DMS kalem bağlantısı uyarlamayla mümkün: TDWO
  `DOKOB=VBAP` × belge türü (ekran 0215); SAPMV45A `MV45AF0D_DOKUMENTE_PFLEGEN` → `DOCUMENT_ASSIGNMENT`. GUI menü yolu DOĞRULANMADI.
- ArchiveLink TOAOM `VBAP` boş; Attachment Service `SAO_TYPE_DEF` yalnız başlık düğümleri (VBAP eklemek = standart tabloya
  yazma → ADR 0005-B yasak). Geliştirme yolu: Z uygulama + `CL_GOS_MANAGER`/`CL_GOS_API` ile `VBAP` anahtarı (released değil).

### SD-D5 VF04 (fatura vade listesi) genişletme: Custom Fields GUI'ye gelmez
- VF04 = SDBILLDL; liste yapısı `VKDFIF` (= `VKDFI` + birkaç alan), ALV `VKDFS_ALV_DISPLAY` (SAPLV60P).
- **GUI kolonu:** CMOD `V60P0001` → `EXIT_SAPLV60P_008` (`TABLES c_vkdfif`, ALV'den hemen önce) + `VKDFIF`'e append
  (standart DDIC — ADR 0005-A, append adı **kullanıcıdan**). `VKDFIZ` "customer reserve" include'u da standarttır.
  `VKDFIF` VF24'te de kullanılır (kolon orada boş görünür).
- **Custom Fields:** context `SD_BILLINGINDEX` persistence'ı yalnız **VKDFS** tablosunda; kullanımı Fiori
  `C_BILLINGDUELISTITEM_F0798` + OData `SD_CUSTOMER_INVOICES_CREATE`; **GUI kullanımı 0** (`CFD_W_GUI_CTXT`) ⇒ VF04 GUI'ye
  saf Custom Fields yolu YOK. Hibrit köprü (VKDFS Custom Field'ı ile aynı adlı VKDFI append'i) **DENENMEDİ**.
- Seçim ekranı: exit yetmez → `ENHANCEMENT-POINT sdbilldl_10` + implicit `FO:VKDFS_DATA_COLLECT\SE:END`.
  Önce "GUI mi Fiori mi" sor.

### SD-D6 Satış belgesi kalemi maliyet yapısı (VA22 ağacı) okuma
- Ağaç bağı: üst kalemin CKIS satırında `UKALN` doluysa alt maliyet hesaplamasına bağlanır; montaj işareti `BAUGR`
  (CDS'te `CostingItemIsAssembly`). Alt seviye KEKO (B tipi) kayıtları **aynı satış belgesi kalemine** yazılır ⇒ kalem başına
  **iki toplu okuma** yeter (KEKO: belge+kalem · CKIS: FAE); seviye başına döngüde okuma gerekmez.
- ATC: `DO` döngüsü içindeki FAE okuması da P1 "Local Nested Reading DB OP" sayılır (BE-12 LOOP/FOR der; DO aynı sınıf).
- `I_SalesDocCostEstimateItem` / `I_SalesDocumentCostEstimate` **released değil**. CKIS `TYPPS` metinleri DD07T domain `TYPPS`'ten.

### SD-D7 ⚠ Teslimat planında (SA, `VBTYP='E'`) VBEP açık miktar için GÜVENİLMEZ — T-SD-5
- **VBEP'in VARLIĞI açık miktar kanıtı değildir:** tamamı sevk edilip kapanmış SA'da da termin satırları durur.
  **YOKLUĞU tek yönlü sağlamdır:** satır yoksa sevk edilecek şey de yoktur. Veri bozuk değil, **semantik farklı**.
- Ölçülen dağılım (tek DEV sistemi): SA belgelerinin ~%45'inde hiç VBEP satırı yoktu.
- Çağrılı SA'da (VBEP-ABART '1'/'2') teslim havuzu `LV45EU11` / `RV_SCHEDULE_CHECK_DELIVERIES` içinde
  **`S073-LIEFFZ` (kümülatif, yıl kuralı) − `VBLB-ABEFZ` (ABRLI='0000')** ile kurulur (`SD_DELIVERY_CUMULATIVE_DETERM`);
  VBEP yalnız havuzun satırlara dağıtıldığı yerdir ⇒ **VBFA üzerine konan süzgeçler SA'da NO-OP'tur**.
- Modellenmeyen sınır: çağrısız SA (ABART başka) FM'de VBFA-RFMNG yoluna düşer — ölçülmedi.

### SD-D8 ⚠ SA çağrı geçmişi (VBLB/VBEH/VBEP) okuma tuzakları — T-SD-5
1. Çağrı sırası = `VBLB-ABRLI`: `0000` güncel; geçmişte **küçük ABRLI daha yeni**, `9999` en eski. Geçmiş termin satırları
   VBEH'te (`0000` yok), güncel olanlar VBEP'te.
2. `ABRLI=9999` ("yaratım kaydı") **içerikli olabilir** — başlığa göre elersen gerçek çağrı düşer; içerik tabanlı süz.
3. Ay satırının (PRGRS=3) `EDATU`'su ayın 1'i olmak zorunda değil.
4. **VBEP'te VBTYP kolonu YOK** — SA süzgeci VBAK join'iyle. Miktar = `WMENG` (`BMENG` farklı olabilir).
5. `ABRDT` kirli olabilir — sıralama/varsayılan seçimi bozar.
6. Malzeme değer yardımı CDS'inin anahtarı yalnız `Matnr` ama satırı MVKE satırıysa join'i `Matnr + Vkorg + Vtweg` ile yap
   (aksi hâlde OData anahtar çakışması + şişen sayım).
7. Belge türü released başlıkta `I_SalesSchedgAgrmt.SalesSchedgAgrmtType`; standart DCL (`V_VBAK_AAT` + `V_VBAK_VKO`)
   Z görünüm üzerinden okumada değerlendirilmez (CDS-DCL-01) ⇒ Z DCL şart.

### SD-D9 Müşteri konsinye stoğunda (SOBKZ=W, `MSKU`) depo yeri boyutu YOK
- `MSKU` anahtarı MATNR/WERKS/CHARG/SOBKZ/KUNNR; LGORT'un anlamı yoktur. Konsinye siparişinde, teslimatta ve mal
  çıkışında (633) LGORT **boştur** ⇒ stok kontrolünü depo yeri bazlı kurma, teslimat/MÇ BAPI'lerine LGORT gönderme.

### SD-D10 Standart satış fiyatı onayı yalnız anahtarında `KFRST` olan koşul tablolarında çalışır — T-SD-2
- S/4 satış fiyatı onayı (`COND_WORKFLOW`, `KONH-PRICEAPPROVALREQUEST`, `KONP-KFRST`) onay sınıfı yalnız anahtarında
  `KFRST` olan koşul tablolarını işler ⇒ erişim sırası tabloları `KFRST` içermiyorsa standart onay devreye giremez
  [kod okumasından çıkarım, canlı denenmedi]. Önce sistemde üçüncü parti bir fiyat onay eklentisi kurulu mu bak.
- Koşul kaydı yazma: released `CL_PRCG_CNDNRECORD_API_FACTORY` → `IF_SLSPRCG_CNDNRECD_API`; RAP
  `I_SlsPrcgConditionRecordTP_2` yazma BDEF'te kapalı; `BAPI_PRICES_CONDITIONS` notReleased.
  Release kanıtı `ARS_W_API_STATE` (`adt_sql_query`) ile okunabilir.

### SD-D11 ⚠ VDA 4905 (çağrı/teslimat planı EDI'si) parse: sabit 128 karakter + KARIŞIK KODLAMA
- Bazı OEM'ler EDIFACT değil **VDA 4905** gönderir: 128 karakterlik sabit kayıtlar, kayıt tipi ilk 3 karakterde (`511`, `512`, …).
- ⚠ **Aynı klasörde karışık kodlama** olabilir (ölçülen korpus: 17 dosya EBCDIC `cp500` + 465 dosya ASCII). Klasöre tek kodlama
  uygulayan parser sessizce çöp üretir ⇒ **dosya başına tespit**:
  `raw=open(p,'rb').read(); enc='ascii' if raw[:3]==b'511' else 'cp500'`.
- Ampirik ofsetler (bir OEM korpusunda ölçüldü, dokümandan değil — kendi korpusunda yeniden ölç): `511 [5:14]` müşteri no ·
  `511 [14:23]` tedarikçi no · `512 [5:8]` fabrika → `KNREF` · `512 [38:60]` müşteri parça no (22 kr.) → `E1EDP10/IDNKD` ·
  `512 [82:92]` `BSTKD` · `512 [94:98]` boşaltma noktası → `ABLAD`. `511 [23:29]` tarih ofseti DOĞRULANMADI.
- ⚠ **Parça no dolgu varyantı:** 22 karakterlik alan = 11 parça no + 11 ek alan; aynı parça iki farklı dolgu karakteriyle
  (sıfır / boşluk) gelebilir. CPI ham alanı normalize etmiyorsa `KNMT`'de **her yazım için ayrı satır** gerekir; eksik `KNMT`
  `V4 035` verir. Otorite = orijinal mesaj dosyası, DEV IDoc'u değil.
