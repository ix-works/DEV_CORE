---
applies_to: [s4_private]
layer: L3
scope: project-wide
type: playbook
applies-to: backend
last-updated: 2026-11-08
status: active
---

# BAdI Enhancement Spot (ENHS/XSB) + BAdI Tanımı

> **Kanonik araç:** 📦 [`scripts/populate_badi_spot.py`](../scripts/populate_badi_spot.py) (lib:
> `sap_adt_lib` `get/create/write/activate_enhancement_spot` + `enhs_*` yardımcıları).
> **MCP yüzeyi YOK — bu CLI kullanılır** (açık kalem: §7).
> **Ölçüm — iki sürümde ölçüldü:** bir geliştirme sistemi (SAP_BASIS 758) + bir tüketici sistemi
> (SAP_BASIS 816), ikisi de `$TMP`'de sentetik spot'la (DEV_CORE #413). Hangi davranışın hangi
> sürümde ölçüldüğü satırında etiketlidir: **[758]** · **[816]** · **[758+816]**; ikisinde de
> ölçülmeyen **ÖLÇÜLMEDİ** yazılıdır. SAP kaynak okuması **[kaynak]** etiketlidir. Profil: `s4_private`.
> prior-art: yok — çekirdekte ENHS yazma yolu ilk temas (`git log -S enhsxsb` 0 commit;
> `lessons-learned` / `removed-controls` içinde ENHS kaydı 0).

## 1. Kullanım

```powershell
# oku (yazma yok, transport gerekmez)
python scripts/populate_badi_spot.py --spot ZSD001_ES_ORNEK --show

# yeni spot + ilk BAdI tanımı (spot yoksa boş kabuk yaratılır)
python scripts/populate_badi_spot.py --spot ZSD001_ES_ORNEK --transport <TR> `
    --package ZSD001 --description "Örnek BAdI noktası" `
    --badi ZSD001_BADI_ORNEK --interface ZIF_SD001_BADI_ORNEK --shorttext "Örnek BAdI" `
    --coklu-kullanim hayir --fallback-class ZCL_SD001_BADI_ORNEK_FB `
    --sample-class ZCL_SD001_BADI_ORNEK_EX --filter ULKE C "Ülke" --filter-check ULKE LAND

# yalnız bir alanı değiştir (diğer tanımlar ve alanlar canlı belgeden korunur)
python scripts/populate_badi_spot.py --spot ZSD001_ES_ORNEK --transport <TR> `
    --badi ZSD001_BADI_ORNEK --shorttext "Yeni kısa metin"

# N tanımı TEK PUT'ta ekle/güncelle (spec dosyası; silme spec'te YOK)
python scripts/populate_badi_spot.py --spot ZSD001_ES_ORNEK --transport <TR> --spec tanimlar.json

# kaldırma YALNIZ açık bayrakla
python scripts/populate_badi_spot.py --spot ZSD001_ES_ORNEK --transport <TR> `
    --badi ZSD001_BADI_ORNEK --remove-filter ULKE
```

Spec biçimi (her öğe bir tanımı **ekler ya da günceller**; verilmeyen alan canlıdaki değeriyle kalır;
spec'te olmayan tanım canlıdaki hâliyle KORUNUR):

```json
{"tanimlar": [
  {"badi": "ZSD001_BADI_ORNEK", "interface": "ZIF_SD001_BADI_ORNEK", "shorttext": "Örnek BAdI",
   "coklu_kullanim": "hayir", "fallback": "ZCL_SD001_BADI_ORNEK_FB",
   "ornek": ["ZCL_SD001_BADI_ORNEK_EX"],
   "filtreler": [{"ad": "ULKE", "tip": "C", "kisa": "Ülke", "dtel": "LAND"}]}
]}
```

Bayraklar: `--remove-badi` · `--remove-fallback-class` · `--remove-sample-class` · `--remove-filter` ·
`--coklu-kullanim evet|hayir` · `--dry-run` (belgeyi basar, yazmaz) · `--no-activate`.
⚠ **`--coklu-kullanim evet` ⇒ `enhs:singleUse="false"`** (ters eşleme; `singleUse="true"` = tek
kullanım = `BADI_MAIN-SINGLE_USE = X` **[758]**; "çoklu kullanım: evet → `false`" standart spot'ların
canlı XML'iyle **[816]**). Çıkış: `0` tamam · `1` akış hatası (HTTP / kilit / aktivasyon / readback) ·
`2` kullanım ya da koruma reddi (**SAP'ye istek gitmeden** ya da yazmadan önce). `--transport` her
yazmada zorunlu — numarayı kullanıcıya sor, uydurma.

## 2. Ölçülen uçlar ve sıra

| Adım | İstek | Ölçülen sonuç |
|---|---|---|
| Ad doğrulama | `POST /sap/bc/adt/enhancements/enhsxsb/validation?objname&objtype=ENHS/XSB&packagename&description` | **[758]** 200 `<CHECK_RESULT>X</CHECK_RESULT>`; 43 karakterlik ad → 400 `InvalidObjName`, T100 `SWB_TOOL 017` V1=`30` ⇒ **spot adı en çok 30** |
| Yaratma | `POST /sap/bc/adt/enhancements/enhsxsb?corrNr=<TR>` gövde `<enhs:badiDefinitions/>` | **[758+816]** 201 + `Location: …/enhsxsb/<ad küçük harf>`. **[758]** içerikli tek POST da içeriği kaydetti — araç yine boş kabuk + PUT kullanır |
| Kilit | çekirdek `lock_object`: `/locks` 404 → `/core/objectlock` 404 → nesne URL'i `?_action=LOCK&accessMode=MODIFY&corrNr=` **200** | **[758+816]**; yanıtta `CORRNR` boş (`$TMP`), **[758]** `MODIFICATION_SUPPORT` de boş |
| Yazma | `PUT …/enhsxsb/<ad>?corrNr=&lockHandle=` tam belge | **[758+816]** 200. **[758]** kilitsiz PUT → 400 `ExceptionParameterNotFound` "lockHandle" (`SADT_RESOURCE 017`) |
| Kilit bırak | `POST …?_action=UNLOCK&lockHandle=` | 200 — araç bunu `finally`'de yapar (PUT 4xx/istisnada da) |
| Aktivasyon | çekirdek `activate_object(..., object_type='ENHS/XSB')` | **[758]** 7/7 `activationExecuted=true` (`adtcore:type="UNKNOWN"` ile de aktive oldu; mekanizma ÖLÇÜLMEDİ) · **[816]** her kademede `activationExecuted=true` |
| Silme | kilit → `DELETE …/enhsxsb/<ad>` | **[816]** 200; aktif, inaktif ve sürümsüz GET üçü de 404, worklist 0. **Bu araçta silme YOK**; çekirdek `adt_delete` ENHS'i desteklemiyor (`object_types.get_object_url` → `ValueError: Unsupported object type`) — açık kalem §7 |

İçerik tipi (Accept + Content-Type): `application/vnd.sap.adt.enh.enhs.v2+xml`. İlk yazma isteği
`403 CSRF` + `GET /discovery 406` + yeniden deneme verir — çekirdek token yenileme deseni, hata değil.

Sürüm başına ölçülen içerik: arabirim · örnek sınıf · DictionaryCheck'li `C` filtresi **[758+816]** ·
yedek (fallback) sınıf · `I` tipi filtre · kilitsiz PUT 400 · tek POST **[758]** · kontrolsüz `C` filtresi ·
silme **[816]**.

**Aktivasyon SIRASI (kural):** ① BAdI arabirimi + fallback/örnek sınıflar ÖNCE aktif ② sonra
spot + BAdI tanımı ③ BAdI'ye atıf yapan sınıflar (implementasyon, `GET BADI` çağıranı) EN SON.
Ölçümde ① aktifken ② temiz aktive oldu **[758+816]**; ters sıra ÖLÇÜLMEDİ.

## 3. ⛔ Tuzaklar

1. **PUT TAM BELGEDİR — hem filtre hem BAdI listesi için.** **[758]** iki filtreli tanıma tek
   filtreli belge gönderildi → ikinci filtre sunucuda **SİLİNDİ** (`BADI_FILTER` 2→1).
   **[kaynak]** `CL_ENH_ADT_BADI_DEF_CONT_SVC->SET_DATA_TO_TOOL` önce TÜM tanımları siler, sonra
   gövdedekileri ekler ⇒ gövdede olmayan BAdI tanımı da silinir. Araç belgeyi **daima taze GET'ten**
   kurar, yalnız verilen tanımı/alanı değiştirir; diğer tanımlar okunan belgeden aynen gider;
   kaldırma yalnız `--remove-*`. GET belgesi aracın modellemediği alan taşıyorsa (bilinmeyen
   eleman/öznitelik, Dictionary dışı filtre kontrolü, dolu `documentationId`) araç **yazmaz**.
2. **GÖVDE SIRASI — çalışma alanı tuzağı (kaynakta doğrulandı, canlıda tetiklenmedi).**
   **[kaynak, 758; aynı bulgu 816 kaynak okumasında]** aynı yöntemde silme döngüsü
   (`LOOP AT l_badi_datas INTO l_badi_data`) bitince çalışma alanında SON eski tanım kalır; gövdenin
   her tanımı için `READ TABLE l_badi_datas WITH KEY badi_name = … INTO l_badi_data` bulunamazsa
   çalışma alanı DEĞİŞMEZ, `CLEAR l_badi_data` yalnız döngü sonunda koşar ⇒ gövdenin **İLK** tanımı
   canlıda yoksa yeni tanım son eski tanımın üzerine yazılmayan alanlarını devralır (metin
   kimlikleri; `badi_filters_copy` üzerinden aynı adlı filtrenin `filtertext_id`'si — iki BAdI aynı
   metin kimliğini paylaşır). **Araç kuralı:** gövdede ÖNCE canlıda var olan tanımlar (canlı
   sırasıyla), yeni tanımlar SONA (`add_badi_def` append eder; sıra yalnız gösterimdir).
   Canlıda tanım varken gövdedeki tanımların HİÇBİRİ canlıda yoksa tuzak kaçınılmazdır ⇒ araç
   **REDDEDER** (`sira_tuzagi`); iki adımda yap: önce yenileri ekle (eskiler korunur), sonra
   eskileri `--remove-badi` ile kaldır. Gerekçe: otomatik iki-PUT yolu yarıda kalırsa spot ara
   hâlde kalır; iki açık komut her adımı kendi aktivasyon + readback'iyle doğrular.
   Aynı yöntemden **[kaynak]**: filtre tipi `badi_filter_types` tablosuna karşı denetlenir (e038) ·
   boş tanım/filtre adı e036/e037 · `amdp=true` ⇒ HDB. Araç yeni filtrede yalnız ölçülen `C`/`I`
   tipini ve boş olmayan adı kabul eder; `amdp` okunan değeriyle korunur, ayarlanmaz.
3. **Aktiflik = sürümsüz GET + worklist + `activationExecuted`; `?version=` AKTİFLİK KANITI DEĞİL.**
   **[758+816]** aktivasyondan önce `?version=active` 200 + `adtcore:version="active"` + **inaktif
   içerik** döner; aktivasyondan sonra `?version=inactive` de `version="active"` der (asimetrik yankı).
   **[758]** sürümsüz GET 13/13 yazım sonrası `inactive`, 11/11 aktivasyon sonrası `active` ⇒ ayıran
   tek okuma **sürümsüz GET**. Araç hükmü: `activationExecuted` + worklist'te yok + sürümsüz GET `active`.
4. **Worklist spot'u başka adla listeler** **[758+816]**: `adtcore:type="ENHS/XS"` +
   `…/enhancements/enhsxs/<ad>` (istek `ENHS/XSB` + `…/enhsxsb/<ad>`). URI ya da tam tiple eşleştiren
   sonda inaktif spot'u **GÖREMEZ** — hedef `{'name': <AD>, 'type': 'ENHS'}` (`enhs_worklist_hedefi`).
   ⚠ Çekirdek `activate_object`'in kendi kesinleştirmesi (gövde hüküm taşımadığında) URI + tam tiple
   kurar ⇒ ENHS'te o yol kördür; `activate_enhancement_spot` kendi sondasını ayrıca koşar.
5. **Sunucu eklentileri** **[758+816]**: `contentCommon/enhs:usages` (sunucu doldurur), `customLogicRegistered`,
   boş `documentationId`, `atom:link`, `contentCommon@internal*` — yazmada GÖNDERİLMEZ, readback
   kıyasında `sunucu_ek` olarak ayrı basılır, kıyasa girmez.

## 4. Belge biçimi (ölçülen, kabul edilmiş PUT **[758]**)

```xml
<enhs:objectData xmlns:enhs="http://www.sap.com/adt/enhancements/enhs" xmlns:adtcore="http://www.sap.com/adt/core"
  xmlns:enhcore="http://www.sap.com/abapsource/enhancementscore" adtcore:name="ZSD001_ES_ORNEK"
  adtcore:type="ENHS/XSB" adtcore:description="…" adtcore:language="TR" adtcore:masterLanguage="TR">
 <adtcore:packageRef adtcore:name="ZSD001"/><enhs:contentCommon enhs:toolType="BADI_DEF"/>
 <enhs:contentSpecific><enhs:badiTechnology><enhs:badiDefinitions>
  <enhs:badiDefinition enhs:name="ZSD001_BADI_ORNEK" enhs:shorttext="…" enhs:singleUse="true"
    enhs:useFallbackClass="true" enhs:filterLimitation="false" enhs:contextMode="N" enhs:amdp="false" enhs:internalUse="false">
   <enhs:interface adtcore:uri="/sap/bc/adt/oo/interfaces/zif_sd001_badi_ornek" adtcore:type="INTF/OI" adtcore:name="ZIF_SD001_BADI_ORNEK"/>
   <enhs:defaultClass adtcore:uri="/sap/bc/adt/oo/classes/…" adtcore:type="CLAS/OC" adtcore:name="…"/>
   <enhs:sampleClasses><enhs:sampleClass adtcore:uri="…" adtcore:type="CLAS/OC" adtcore:name="…"/></enhs:sampleClasses>
   <enhs:filters><enhs:filter enhs:filterName="ULKE" enhs:filterType="C" enhs:shorttext="…">
    <enhs:filterCheck xsi:type="enhcore:DictionaryCheck" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
     <enhcore:checkObject adtcore:uri="/sap/bc/adt/ddic/dataelements/land" adtcore:type="DTEL/DE" adtcore:name="LAND"/>
    </enhs:filterCheck></enhs:filter></enhs:filters>
  </enhs:badiDefinition></enhs:badiDefinitions></enhs:badiTechnology></enhs:contentSpecific></enhs:objectData>
```

Kontrolsüz filtre: `<enhs:filter enhs:filterName=… enhs:filterType="C" enhs:shorttext=…/>` **[758+816]**.
Fixture `tests/fixtures/enhs_badi_spot` (S2): ölçülen readback'ten kurulan belge, ölçülen kabul
edilmiş PUT ile **bayt-eşit**. Yeni tanımın varsayılanları ölçülen ilk PUT'unkilerdir
(`singleUse=true`, `contextMode=N`, diğer bayraklar `false`).

## 5. Koruma (ADR 0005-A — yeni kural değil)

Spot ve BAdI adı `utils.ad_politikasi.musteri_karari`'ndan geçer (Z/Y ya da projede
`customer_namespaces` ile bildirilmiş `/<NS>/`); değilse CLI **istek göndermeden** `2` döner.
İkinci katman: lib yazmadan hemen önce GET eder — `adtcore:masterSystem="SAP"` ya da standart
adlı tanım taşıyan belgeye yazmaz. BAdI adı sınırı 30: AFF şemasından, canlıda **ÖLÇÜLMEDİ**.
`--show` da ad denetiminden geçer (araç yazma aracıdır; standart spot okumak için `adt_get`).

## 6. Sınırlar / ÖLÇÜLMEDİ

- Birden çok BAdI'li gövde canlıda ÖLÇÜLMEDİ (iki sürümde de tek tanım); çoklu tanım davranışı
  kaynak okumasına ve tek-tanım ölçümlerine dayanır. Sıra tuzağı canlıda tetiklenmedi.
- Fallback kaldırma (`true→false`), örnek sınıf kaldırma, son tanımı kaldırma (boş `badiDefinitions`
  PUT), filtre tipini değiştirme (araç reddeder), `contextMode` S/Y, ProgramCheck filtresi, çeviri,
  transport'lu pakette kabuk POST'u **ÖLÇÜLMEDİ**.
- Kilit son hâli bağımsız araçla ÖLÇÜLEMEDİ (`adt_lock_check` ENHS desteklemiyor); dayanak
  LOCK 200 ↔ UNLOCK 200 istek kaydıdır, SM12 kontrolü kullanıcıdadır.

## 7. Kapsam dışı / açık kalemler

- **Silme:** ölçülmüş yol (bir tüketici sisteminde, SAP_BASIS 816) kilit → `DELETE` → 200; çekirdek
  `adt_delete` ENHS'i desteklemiyor — açık kalem (`object_types`'a `enhsxsb` girdisi bu PR'da eklenmedi).
- **MCP aracı** (`adt_*`) yok — o zamana kadar bu CLI.
- BAdI implementasyonu (ENHO), `CL_ENH_*` API'leri, `adt_enhancement_read` enhoxhb yanlış-negatifi,
  `adt_lock_check`'in ENHS'i desteklememesi bu aracın kapsamı dışında.
