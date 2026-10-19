---
applies_to: [s4_private]
---

# HOWTO — Klasik varyant konfigürasyonu (LO-VC): satış belgesi konfigürasyonunu okuma ve değiştirme

> **Ne zaman açılır:** konfigüre edilebilir malzemeli bir satış belgesinde (teklif / sipariş) şunlardan
> biri istendiğinde:
> - *"kalemlerin karakteristik değerlerini raporda göster / süz"*
> - *"karakteristik değerini programdan değiştir"* ya da *"değeri değiştirdik ama bağımlılıklar tetiklenmedi"*
> - *"RAP / Fiori'den konfigürasyon değeri yaz"*
>
> **Ne anlatır:** motor tipini nasıl ayırt edersin, belge değerini nereden okursun (released durumu
> dahil), kaydedilmemiş belgede ne çağırırsın, değeri hangi yolla değiştirirsin ve sessiz başarısızlık
> tuzakları. AVC (Advanced Variant Configuration) yalnız ayrım ve karşılaştırma için anılır.
>
> **Kanıt düzeyi (her satırda etiket):** bir s4_private 2025 sisteminde, 2026-10-19.
> - **[Ç]** teslim edilmiş bir raporda çalışıyor, kullanıcı testi OK.
> - **[Ö]** ölçüldü (SQL / ARS / DDL okuması).
> - **[K]** SAP kaynak kodu okunarak çıkarıldı, **çalıştırılmadı**.
> - **[DV]** doğrulanamadı.
> - **[W]** internet kaynağı (hipotez).
>
> ⛔ Başka sürüm ya da sistemde her adımı canlıda teyit et. Released durumu sürüme bağlıdır. **[K]**
> etiketli yazma tarifi çalıştırılarak doğrulanmadı: koda girmeden önce test sisteminde dene.
> ADR 0005-B: IBIN* / VBAP / PRCD_ELEMENTS'e doğrudan yazma YASAK.

## 0. Önce motor tipini ölç — klasik mi AVC mi

| Ölç | Klasik LO-VC | AVC |
|---|---|---|
| Profil `CUCO-PROC_MODE` (domain `CU_PROC_MODE`) | boş | `A` |
| Bağımlılık tipi `CUKB-KNART` | 5 seçim koşulu, 7 prosedür, … | AVC sözdizimi |

Kip **profil başına** seçilir; aynı sistemde ikisi yan yana durabilir. **[Ö]**

AVC'ye özgü yollar klasik modelde kullanılamaz: `R_VariantConfigurationTP`, VCH API'leri ve
`I_VarCnfProductProfileTP`. Sonuncusu released'tır ama DDL zincirinin sonunda `where proc_mode = 'A'`
vardır, klasik profilde 0 satır döner. **[Ö]**

⚠ Kalite client'ında model kurulu, geliştirme client'ında iskelet olabilir. Kodu ad üzerinden yaz
(bkz. §5-1) ve testi modelin olduğu client'ta yap.

## 1. Kaydedilmiş belgenin değerlerini okuma

### 1.1 Released durumu (`ARS_W_API_STATE`, s4_private 2025)

| Konu | Released — tercih et | Released DEĞİL |
|---|---|---|
| Malzeme | `I_Product` | — |
| Malzeme → sınıf | `I_ClfnObjectClassForKeyDate` (**malzeme adıyla** sorgulanır) | `I_ClfnObjectClassBasic` (iç CUOBJ ister; malzeme adıyla 0 satır) |
| Sınıf | `I_ClfnClass`, `I_ClfnClassForKeyDate`, `I_ClfnClassDescription` | — |
| Sınıf → karakteristik | `I_ClfnClassCharcForKeyDate` | `I_ClfnClassCharcBasic` |
| Karakteristik | `I_ClfnCharacteristic(ForKeyDate)`, `I_ClfnCharcDesc(ForKeyDate)` | `I_ClfnCharcBasic` |
| İzinli değer + metin | `I_ClfnCharcValue(ForKeyDate)`, `I_ClfnCharcValueDesc(ForKeyDate)` | — |
| Profil (klasik) | — (`I_VarCnfProductProfileTP` yalnız AVC) | `I_ConfigurationProfile` (CUCO ile birebir) ya da CUCO |
| Teklif kalemi | `I_SalesQuotationItem` (`ProductConfiguration` = `VBAP-CUOBJ`) | — |
| **Belge kalemi değerleri** | **YOK** | `A_/I_/P_SlsDocItmVarConfign`, `I_IBaseCharcValue` |

⚠ Adında `…Basic` geçenler ve `I_ConfigurationProfile` released değildir. Ad benzerliğine bakıp
"released" yazma; ARS'te ölç. **[Ö]**

Ana veri okumasında `…ForKeyDate( p_keydate = @sy-datum ) WITH PRIVILEGED ACCESS` kullanılır. **[Ç]**

### 1.2 Belge kalemi → değer zinciri (released view yok)

```
VBAP.CUOBJ
 → IBINOWN   (instance = cuobj, inttyp = '0001', delflag = space; objkey = VBELN(10)+POSNR(6))
 → IBIN      (instance; klart = '300', delflag = space, valfr <= ts <= valto  — DEC 15 zaman damgası)
 → IBINVALUES(in_recno; in_segmcnt, currency, curr_value_from/to, dec_value_from/to, date_from/to, ataut)
 → IBSYMBOL  (symbol_id; atinn, atwrt, atcod, atflv)
 → CABN (atinn)   · metin: CAWN / CAWNT  — LEFT OUTER
```

Zincirin dört join'li SQL'i (`FOR ALL ENTRIES` CUOBJ listesiyle, `atinn IN` aralığıyla) çalışan bir
raporda kullanılıyor. **[Ç]**

| Değer tipi | Nerede |
|---|---|
| CHAR | `IBSYMBOL-ATWRT` (iç değer; metin CAWNT'ten) |
| NUM | `IBINVALUES-DEC_VALUE_FROM/TO` (DEC 31,14) ya da `IBSYMBOL-ATFLV` |
| CURR | `IBINVALUES-CURRENCY` + `CURR_VALUE_FROM/TO` |
| DATE | `IBINVALUES-DATE_FROM/TO` |
| Değerin kaynağı | `IBINVALUES-ATAUT`: boş = kullanıcı · `7` = prosedür · `8` = varsayılan **[Ö]** |

**Sessiz hata tuzakları:**
- `IBINVALUES`'te **ATINN yoktur**: karakteristik `IBSYMBOL` üzerinden bulunur. Yanlış kolonla SQL
  "Unknown column" verir. **[Ö]**
- Belge konfigürasyonu **IBINOWN**'dadır, INOB'da değil. INOB malzemenin **sınıflandırmasını**
  (KLART 300) taşır. **[Ö]**
- `I_ClfnObjectCharcValForKeyDate` (released) AUSP sınıflandırma değerini okur; belge
  konfigürasyonunu **vermez**. **[Ö]**
- Metin join'i INNER yapılırsa sayısal / serbest değerler kaybolur, çünkü onların CAWN satırı yoktur.
  Ölçülen vakada 125 değerin 80'i kayboldu. **[Ö]**

### 1.3 Hazır view'lar (released değil)

| View | Artı | Eksi |
|---|---|---|
| `A_SlsDocItmVarConfign` | SalesDocument/Item anahtarlı; teklif + sipariş | Değer metin olarak (`'10.00000000000000'`); **para birimi yok**; değer kaynağı yok |
| `I_IBaseCharcValue` | Ham sayı + tutar + **para birimi** + değer kaynağı | Belge anahtarı yok; IBIN / IBINOWN ile bağlanır |

Bunlardan birini kullanacaksan tek bir Z sarmalayıcıda (interface view ya da tek okuma metodu) topla.
Böylece released olmayan bağımlılık tek yerde kalır ve where-used ile izlenir (clean core:
`balanced`).

## 2. Kaydedilmemiş belge (çıkış / BAdI içinde) **[K]**

| Durum | Okuma | Not |
|---|---|---|
| Konfigürasyon diyaloğu **kapandı** | `VC_I_GET_CONFIGURATION`; yan etkisiz alternatif `CUCB_GET_CONFIGURATION` / `CUCB_GET_VALUES_FROM_INSTANCE` | CBase diyalog bitişinde `CE_C_SET_CBASE` ile dolar; F12 ile çıkılırsa güncellenmez |
| Diyalog **açık** (CEI0 / CUKO çıkışı) | `CE_I_GET_CONFIGURATION` / `CEI0_DDB_HAS_VALUES` | Burada `VC_I_GET_CONFIGURATION` ÇAĞIRMA — CEI0 tamponunu yeniden kurar |
| Kaydedilmiş, FM ile | `VC_I_GET_CONFIGURATION_IBASE` | CBase üzerinden okur. Değişiklik oturumunun içinde kaydedilmemiş durumu verebilir; yalnız oturum dışında kullan |

`VC_I_GET_CONFIGURATION` önce AVC adaptörüne gider. Profil klasikse `delegation_denied` ile klasik
gövdeye düşer. **[K]**

Diyalog hiç açılmadan (otomatik konfigürasyon) CBase'in nasıl dolduğu ölçülmedi. **[DV]**

## 3. Karar tablosu

| | Okuma | Yazma |
|---|---|---|
| Kaydedilmiş belge | §1.2 zinciri ya da Z sarmalı view | Teklif: `BAPI_CUSTOMERQUOTATION_CHANGE` (§4) — GUI'de doğrudan, RAP'te Z RFC FM içinde. Sipariş için `BAPI_SALESORDER_CHANGE` aynı CFGS yapısını taşır ama bu araştırmada okunmadı **[DV]** |
| Kaydedilmemiş belge | §2 | Önerilen yol yok — MV45AFZZ'den `CE_I_SET_CONFIGURATION` / `CEI0_DDB_SET_VALUE` ile yazmanın bağımlılıkları tetiklediği doğrulanamadı **[DV]** |
| Ana veri | Released `I_Clfn*ForKeyDate` + `I_Product` | — |

Teklif **yaratma** BAPI'si vardır: `BAPI_QUOTATION_CREATEFROMDATA2` (FG SAPL2031, `_CHANGE` ile aynı
grup). **[Ö TFDIR]** ⚠ Yalnız `BAPI_CUSTOMERQUOTATION%` deseniyle aranırsa bulunamaz ve yanlışlıkla
"yok ⇒ BDC" sonucuna varılır. Released `I_SalesQuotationTP` konfigürasyon taşımaz. **[Ö]**

## 4. Değer değiştirme — bağımlılıkların gerçekten çalışması için

### 4.1 Yöntemler

| Yöntem | Bağımlılıklar koşar mı | Kullan? |
|---|---|---|
| **`BAPI_CUSTOMERQUOTATION_CHANGE`** (CFGS_* tabloları) | **Evet** — IDoc kipi: `CE_I_CONFIGURE` → `CUKO_DDB_CONFIGURE_ITEM` → `CUKO_CHECK_CONFIGURATION` → `CUKO_DDB_CONFIGURATION_FINISH` **[K]** | **Birincil yol** (released değil; std 10 sırası) |
| `SD_SALESDOCUMENT_CHANGE` doğrudan | Aynı (BAPI'nin içi) | Hayır (iç FM) |
| `CFGS_REF-SCE = '1'` | **Hayır** — CBase'e doğrudan yazar | Hayır |
| `CUXI_SET_*`, `CUCB_SET_*` | **Hayır** | Hayır |
| `CE_I_SET_CONFIGURATION`, `CEI0_DDB_SET_VALUE` | Kısmi / doğrulanamadı | Hayır |
| BDC VA22 | Beklenir (tam diyalog), doğrulanmadı | Yalnız BAPI yetmezse |
| EML `R_VariantConfigurationTP` | AVC yığını; SD kalemine yazmaz | **Hayır** |
| IBIN* / VBAP / PRCD_ELEMENTS'e SQL | — | ⛔ **YASAK** (ADR 0005-B) |

### 4.2 Tarif (GUI Z programından) **[K — çalıştırılmadı]**

1. **Oku:** mevcut konfigürasyonu (§1.2) ve kalemin **`VBAP-POSEX`** değerini al.
2. **⚠ Sessiz atlama — iki kapı.** SD konfigürasyonu uygulamaz ve **hata dönmez**:
   - (a) `CFGS_REF-POSEX` kalemin POSEX'iyle eşleşmezse;
   - (b) kalemin **`VBAP-POSEX`'i boşsa**. Bu durum VA21/VA22'de açılan belgede tipiktir: ölçülen bir
     sistemde 770 kalemin 761'inde POSEX boştu. **[Ö]**

   Kanıt: `FV45SFCO_CONFIGURATION_CHECKI1` FORM `CONFIGURATION_CHECK_IDOC_MODE` →
   `IF VBAP-POSEX IS INITIAL AND KOPIEREN EQ SPACE AND FCODE NE FCODE_KONFIGURATION → CH_SUBRC = 8`.
   Ardından `PROCES1` içinde `CHECK ch_subrc < 8 OR us_background NE space`. BAPI yolunda
   `us_background` değeri okunmadı. **[K + DV]**

   **Çözüm adayı [DV]:** aynı çağrıda `QUOTATION_ITEM_IN-PO_ITM_NO` + `…INX-PO_ITM_NO = 'X'` ile POSEX'i
   doldur ve `CFGS_REF-POSEX` = aynı değer ver.

   ⚠ POSEX müşteri sipariş kalem numarası alanıdır. Doldurmanın kopyalama, çıktı ve EDI etkisini önce
   değerlendir.
3. **BAPI parametreleri:**
   - `HEADER_INX-UPDATEFLAG = 'U'`. `ITEM_IN` / `ITEM_INX`: `ITM_NUMBER`, `UPDATEFLAG = 'U'` ve değişen
     alanın X'i. X'siz alan değişmez; boş göndermek hiç göndermemekle aynı şey değildir.
   - `CFGS_REF`: `POSEX`, `CONFIG_ID`, `ROOT_ID`, **`SCE` boş**.
   - `CFGS_INST`: kök örnek (`INST_ID`, `OBJ_TYPE` / `OBJ_KEY` = malzeme, `CLASS_TYPE` 300).
   - `CFGS_VALUE`: **TAM kullanıcı kümesi** (`ATAUT` boş) + değişen değer.
4. **Commit:** `RETURN`'de `E`/`A` varsa `BAPI_TRANSACTION_ROLLBACK`, yoksa `BAPI_TRANSACTION_COMMIT`.
   BAPI kendisi commit etmez.
5. **Kayıttan sonra yeniden oku:** türetilmiş karakteristikler gerçekten değişti mi? Sessiz atlamayı
   yakalayan **tek** kontrol budur.

### 4.3 Kesinlikle yapma **[K]**

| Yapma | Neden |
|---|---|
| POSEX eşleşmesiz / boş POSEX ile göndermek | Sessiz atlama (§4.2-2) |
| Yalnız değişen değeri göndermek | Mevcut kullanıcı girdisi silinip gelen küme yüklenir ⇒ diğer kullanıcı değerleri gider |
| Prosedürün türettiği değeri (`ATAUT = 7`) "kullanıcı" olarak göndermek | Kullanıcı değerine dönüşür, prosedür bir daha güncelleyemez — **donar**. Okurken `ATAUT = '7'` olanları süz |
| `SCE = '1'` | Motor atlanır |
| `LOGIC_SWITCH-PRICING = 'G'` | Koşullar aynen kopyalanır; değişken fiyat güncellenmez. Aday tercih `O` (yalnız değişken koşullar) |
| Hata sonrası aynı oturumda rollback'siz devam | CFGS bellek hücreleri oturumda kalır |

**Açık soru — varsayılan değerler (`ATAUT = '8'`):** SAP kodu değişiklikte bunları da silip gelen
kümeyi yükler. Gönderilmezse kaybolabilirler; gönderilirse kullanıcı değerine dönüşüp donabilirler.
`LCUXCF01` FORM `FILTER_INBOUND_DATA` gelen değerlerden yalnız AUTHOR boş ve `'8'` olanları tutar.
**[K → test et]**

### 4.4 RAP'ten **[K]**

1. Handler / saver'da `COMMIT WORK` ya da `BAPI_TRANSACTION_COMMIT` yasaktır (`BEHAVIOR_ILLEGAL_STATEMENT`;
   checklist BE-26).
2. Yazma, Remote-Enabled bir Z FM içinde `CALL FUNCTION … DESTINATION 'NONE'` ile yapılır. CFGS
   doldurma + BAPI + commit **aynı FM çağrısında** olmalı (bellek hücreleri oturuma özel). Ayrıntı:
   [`adt-rap.md`](adt-rap.md).
3. BO aynı belgeyi kilitliyorsa ayrı oturumdaki BAPI belgeyi kilitleyemez. **[DV]**
4. Motor hatası varsayılan mesaj tipi `A` ile gelir ⇒ `EXCEPTIONS system_failure = 1 MESSAGE lv_msg`.
5. `DESTINATION 'NONE'` aynı kullanıcıyla yeni oturum açar. Kullanıcıya bağlı varyant fonksiyonları
   (ör. `SY-UNAME` yazan, giriş kapatan) aynı sonucu verir. Arka plan / teknik kullanıcıda sonuç
   farklıdır.

## 5. Tuzaklar (geliştirme sırasında)

1. **İç numaralar client'a özeldir** (CUOBJ, CLINT, ATINN). Kod **ad** ile çalışır (ATNAM, sınıf adı).
   Çevrim `CONVERSION_EXIT_ATINN_INPUT`; SQL'de ATINN 10 hane sıfır dolguludur.
2. **Para birimi:** karakteristik para birimi belge para biriminden farklı olabilir (ölçülen vaka:
   EUR ↔ TRY). Birimi `IBINVALUES-CURRENCY`'den al.
3. Çok değerli karakteristikte aynı ATINN'in birden çok satır (`IN_SEGMCNT`) üretmesi beklenir; veri
   olmadığı için ölçülmedi **[DV]**. Satır / hücre modelini buna göre kur.
4. Bağımlılık kaynağını SQL ile çekerken `CUKN-KNBLK` uzun alandır. JSON çıktı al; tablo çıktısı keser.
5. Konfigürasyonda kullanıcı adı tutan bir karakteristik (`SY-UNAME` türeten varyant fonksiyonu)
   kişisel veridir. Raporda gösterilecekse dikkate al.
6. Test verisi genelde tek belgedir. Değiştiren testten önce **taban görüntü** al (değerler + ATAUT +
   fiyat).

### 5.1 Raporda dinamik karakteristik kolonları **[Ç]**

- Kolonları sınıfın karakteristik sırasıyla `I_ClfnClassCharcForKeyDate` + RTTC ile çalışma zamanında
  üret. DDIC yapısı gerekmez.
- Değeri olmayan hücre boş kalır.
- Belgeyi değiştiren işlemden (VA22) dönüşte listeyi yenilerken kaydın asenkron güncellemesini bekle:
  `CALL TRANSACTION` sonrası `ENQUEUE_EVVBAKE _scope = '1' _wait = abap_true` + koşulsuz `DEQUEUE_EVVBAKE`
  (fail-open). VA22 kayıtta belge kilidini güncelleme görevine devreder **[K]**; kapının etkinliği
  (CALL TRANSACTION'ın ayrı kilit sahibi olması) çalışma zamanında ayırt edici testle ölçülmedi **[DV]**.

## 6. AVC / Public Cloud yaklaşımı (karşılaştırma) **[W]**

- Public Cloud'da klasik LO-VC yoktur. Değer, motorun içinde released BAdI ile atanır:
  `VCH_HL_PRE_VALIDATE_ASSIGN` bağımlılıklardan **önce** koşar. Bu yapıda "tetiklenmedi" sorunu oluşmaz.
- Private sistemde AVC teknik olarak bulunabilir (`PMEVC`, `IF_VCH_HL_*` BAdI'leri). Geçiş profil
  başınadır, ama:
  - prosedürler elle AVC sözdizimine çevrilir;
  - klasik varyant fonksiyonları BAdI olarak yeniden yazılır;
  - **lisans** ayrıca teyit edilmelidir;
  - PP (BOM / rota) sahibi de karar ortağıdır.

  **Önerme; kullanıcıya karar olarak sun.**

## İlgili

- prior-art: komşu `howto-sd-karakteristik-hizli-giris.md` (uyarlama tarafı); belge konfigürasyonu okuma/yazma için core'da önceki kayıt yok.

- Aynı belgede kalemi konfigürasyonuyla devretme: [`howto-sd-karakteristik-hizli-giris.md`](howto-sd-karakteristik-hizli-giris.md)
- Standart veriye yazma API seçimi: [`../standards/10-standart-veriye-yazma-api-secimi.md`](../standards/10-standart-veriye-yazma-api-secimi.md)
- SD referans: [`modules/referans/sd/bapi.md`](modules/referans/sd/bapi.md) · [`modules/referans/sd/tables.md`](modules/referans/sd/tables.md)
