---
applies_to: [s4_private]
layer: L3
scope: project-wide
type: playbook
applies-to: backend
last-updated: 2026-11-11
status: active
---

# BAdI Enhancement Spot (ENHS/XSB) + BAdI Tanımı

> **Kanonik araç:** 📦 [`scripts/populate_badi_spot.py`](../scripts/populate_badi_spot.py) (lib:
> `sap_adt_lib` `get/create/write/activate_enhancement_spot` + `enhs_*` yardımcıları).
> **MCP yüzeyi YOK — bu CLI kullanılır** (açık kalem: §7). Genel MCP araçlarından yalnız
> `adt_delete` ve `adt_lock_check` spot'u tanır (`object_types` `enhancementspot`/`enhs`, Q402 §2a);
> `adt_atc_check` ENHS'i istek göndermeden **kapsam dışı** diye reddeder.
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
yazmada zorunlu — numarayı kullanıcıya sor, uydurma; `--dry-run` yazmadığı için istemez (yalnız GET).
Var olan spot'ta `--description` / `--package` okunan değerden farklıysa araç `2` döner (açıklama
değişikliği ÖLÇÜLMEDİ; sessizce yok sayılmaz). `--cwd` ad denetiminden ÖNCE uygulanır: müşteri ad
alanı o projenin `customer_namespaces`'inden okunur.

## 2. Ölçülen uçlar ve sıra

| Adım | İstek | Ölçülen sonuç |
|---|---|---|
| Ad doğrulama | `POST /sap/bc/adt/enhancements/enhsxsb/validation?objname&objtype=ENHS/XSB&packagename&description` | **[758]** 200 `<CHECK_RESULT>X</CHECK_RESULT>`; 43 karakterlik ad → 400 `InvalidObjName`, T100 `SWB_TOOL 017` V1=`30` ⇒ **spot adı en çok 30** |
| Yaratma | `POST /sap/bc/adt/enhancements/enhsxsb?corrNr=<TR>` gövde `<enhs:badiDefinitions/>` | **[758+816]** 201 + `Location: …/enhsxsb/<ad küçük harf>`. **[758]** içerikli tek POST da içeriği kaydetti — araç yine boş kabuk + PUT kullanır |
| Kilit | çekirdek `lock_object`: `/locks` 404 → `/core/objectlock` 404 → nesne URL'i `?_action=LOCK&accessMode=MODIFY&corrNr=` **200** | **[758+816]**; yanıtta `CORRNR` boş (`$TMP`), **[758]** `MODIFICATION_SUPPORT` de boş |
| Yazma | `PUT …/enhsxsb/<ad>?corrNr=&lockHandle=` tam belge | **[758+816]** 200. **[758]** kilitsiz PUT → 400 `ExceptionParameterNotFound` "lockHandle" (`SADT_RESOURCE 017`) |
| Kilit bırak | `POST …?_action=UNLOCK&lockHandle=` | 200 — araç bunu `finally`'de yapar (PUT 4xx/istisnada da) |
| Aktivasyon | çekirdek `activate_object(..., object_type='ENHS/XSB')` | **[758]** 9 aktivasyonun 9'unda `success=true`; `activationExecuted` 8/9 `true` — 1 `false`: zaten aktif spot'u yeniden aktive etme, spot aktifti (ölçüm özetleri). `adtcore:type="UNKNOWN"` ile de aktive oldu; mekanizma ÖLÇÜLMEDİ · **[816]** her kademede `activationExecuted=true`. Araç hükmü `success`'i okur, `activationExecuted`'ı DEĞİL |
| Silme | kilit → `DELETE …/enhsxsb/<ad>` | **[816]** 200; aktif, inaktif ve sürümsüz GET üçü de 404, worklist 0. **Bu araçta silme YOK** — genel `adt_delete(name, object_type="enhs", transport)` kullanılır (Q402, §2a) |

İçerik tipi (Accept + Content-Type): `application/vnd.sap.adt.enh.enhs.v2+xml`. İlk yazma isteği
`403 CSRF` + `GET /discovery 406` + yeniden deneme verir — çekirdek token yenileme deseni, hata değil.

Sürüm başına ölçülen içerik: arabirim · örnek sınıf · DictionaryCheck'li `C` filtresi · kontrolsüz `C`
filtresi **[758+816]** · yedek (fallback) sınıf · `I` tipi filtre · kilitsiz PUT 400 · tek POST **[758]** ·
silme **[816]**.

**Aktivasyon SIRASI (kural):** ① BAdI arabirimi + fallback/örnek sınıflar ÖNCE aktif ② sonra
spot + BAdI tanımı ③ BAdI'ye atıf yapan sınıflar (implementasyon, `GET BADI` çağıranı) EN SON.
Ölçümde ① aktifken ② temiz aktive oldu **[758+816]**; ters sıra ÖLÇÜLMEDİ.

### 2a. Genel ADT araçlarında ENHS (Q402 / DEV_CORE #415)

`object_types.OBJECT_TYPES['enhancementspot']` (eş anlamlı `enhs` · `enhsxsb` · `enhs/xsb`), URL
`enhs_spot_url` ile aynı. Girdi **işlem-izinlidir**: `get_object_url(ad, tip, islem=…)` ENHS için
yalnız `silme` · `kilit` · `metadata` işlemine URL üretir; `islem` vermeyen ya da başka işlem veren her
çağıran `ValueError` alır. Gerekçe: düz bir girdi `adt_activate` tek-obje yolunu da açardı ve o yolun
worklist sondası tip `ENHS/XSB` ile sorar (worklist `ENHS/XS` listeler, §3.4) ⇒ inaktif spot
"doğrulandı" görünürdü (sahte-yeşil).

| Araç | ENHS'te davranış | Dayanak |
|---|---|---|
| `adt_delete` | kilit (nesne URL'i `_action=LOCK`; `/locks` ve `/core/objectlock` 404) → `DELETE` (`lockHandle` + `corrNr`) → `UNLOCK`; sonra `delete_verified` (GET `*/*` 404) | yol **[816]** #413 + **[758]** 2026-11-09 ölçüm betikleri; çekirdek `delete_object` ile ENHS'te canlı koşu **ÖLÇÜLMEDİ** (Q402 ölçüm betiği hazır, kuru kipi yeşil; canlı koşu ayrı) |
| `adt_lock_check` | spot'u tanır, varlığı okur; kilit durumu `locked: null` + `kilit_belirsiz` | **[758]** salt-okur: `GET /sap/bc/adt/locks?objectRef=` **sınıfta da** 404 ⇒ ENHS'e özgü değil, kilit ucu bu sistemde yok |
| `adt_atc_check` | istek GÖNDERİLMEZ: `error: atc_kapsam_disi`, `finding_count: null` | **[758]** salt-okur ATC: var olan Z spot · standart spot · var olmayan spot · var olmayan sınıf dördü de `FINDING_STATS 0,0,0` + boş obje listesi; bulgulu Z sınıf `0,0,1` + 1 obje ⇒ ENHS'te "0 bulgu" yokluktan ayırt edilemez |
| `adt_activate` · `adt_syntax_check` · `adt_where_used` · `adt_get` · `adt_push_source` | `ValueError` (kanonik araç: `populate_badi_spot.py`) | işlem izin kümesi dışında (fail-closed) |

Metadata okuması (`get_object_structure`) ENHS'te yalnız `Accept: */*` ile 200 döner — classes v2/v4,
`core.v1`, `application/xml` 406 **[758]**; var olmayan spot `*/*` ile 404.

## 3. ⛔ Tuzaklar

1. **PUT TAM BELGEDİR — hem filtre hem BAdI listesi için.** **[758]** iki filtreli tanıma tek
   filtreli belge gönderildi → ikinci filtre sunucuda **SİLİNDİ** (`BADI_FILTER` 2→1).
   **[kaynak]** `CL_ENH_ADT_BADI_DEF_CONT_SVC->SET_DATA_TO_TOOL` önce TÜM tanımları siler, sonra
   gövdedekileri ekler ⇒ gövdede olmayan BAdI tanımı da silinir. Araç belgeyi **daima taze GET'ten**
   kurar, yalnız verilen tanımı/alanı değiştirir; diğer tanımlar okunan belgeden aynen gider;
   kaldırma yalnız `--remove-*`. GET belgesi aracın modellemediği alan taşıyorsa (bilinmeyen
   eleman/öznitelik, Dictionary dışı filtre kontrolü, dolu `documentationId`) araç **yazmaz**.
   Lib bu denetimi **kilit ALTINDA yeniden** koşar: okuma ile kilit arasında belgeye modellenmeyen
   alan girdiyse ya da modellenen alanlar çağıranın okuduğu tabandan farklıysa PUT gitmez
   (`kilit_alti:` / `taban_degisti:`; kilit bırakılır, yeniden oku ve tekrar dene). Yeniden kurma
   yapılmaz: lib değişikliği değil sonuç modelini alır, üstüne yazmak araya gireni siler.
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
3. **Aktiflik = aktivasyon `success` + worklist + sürümsüz GET; `?version=active` AKTİFLİK KANITI DEĞİL.**
   **[758+816]** aktivasyondan önce `?version=active` 200 + `adtcore:version="active"` + **inaktif
   içerik** döner (yankı). **[758]** 20 okumalık ölçüm (her adımda üç GET biçimi; kaynak: ölçüm
   özetlerinin `get_varsayilan` / `get_active` / `get_inactive` alanları): sürümsüz GET 10 yazma
   sonrası okumanın 10'unda + hiç aktive edilmemiş spot okumasında `inactive`, 9 aktivasyon sonrası
   okumanın 9'unda `active` · `?version=active` 20/20 `active` · `?version=inactive` 20/20 sürümsüz
   GET ile aynı (aktivasyondan sonra `active` döner, yankı DEĞİL). Araç hükmü sürümsüz GET'i okur
   (tek yüzey): `success` + worklist'te yok + sürümsüz GET `active`.
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
"Yalnız sabit filtre değerleri" (`BADI_FILTER-CONSTANT`): **[758, salt-okur GET]** standart bir
spot'un üç filtresinde de `enhs:onlyConstantFilterValues="true"` (shorttext'ten sonra); bayraksız
filtrede öznitelik YOK. Araç `="true"`yu okur, PUT'ta aynı filtrede korur, readback'te kıyaslar;
başka değer biçimi (ör. `="false"`) ÖLÇÜLMEDİ ⇒ modellenmeyen, yazma yok. Özniteliği taşıyan PUT'un
kabulü ÖLÇÜLMEDİ (yalnız GET ölçüldü; standart spot'a yazılmaz).
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
- Türkçe karakterli filtre adı: araç reddetmez, SAP'nin kabulü **ÖLÇÜLMEDİ**.
- DOMA (alan) kontrollü ya da ProgramCheck'li filtre: araç modellemez ⇒ o spot'a yazmaz; yazma
  biçimi **ÖLÇÜLMEDİ**.
- Kilit son hâli bağımsız araçla ÖLÇÜLEMEDİ: `adt_lock_check` spot'u tanır (Q402) ama kilit ucu
  `GET /sap/bc/adt/locks` bu sistemde her tipte 404 ⇒ `locked: null`. Dayanak LOCK 200 ↔ UNLOCK 200
  istek kaydıdır, SM12 kontrolü kullanıcıdadır.

## 7. Kapsam dışı / açık kalemler

- **Silme:** KAPANDI (Q402) — genel `adt_delete` (§2a).
- **ATC:** kapsam dışı (§2a ölçümü). BAdI arabirimi ve sınıfları için ATC o objelerde koşulur.
- **MCP aracı** (`adt_*`) yok — o zamana kadar bu CLI. `adt_activate` ENHS'te bilerek kapalı
  (worklist tip uyuşmazlığı); aktivasyon `populate_badi_spot.py` / `activate_enhancement_spot`.
- BAdI implementasyonu (ENHO), `CL_ENH_*` API'leri, `adt_enhancement_read` enhoxhb yanlış-negatifi
  bu aracın kapsamı dışında.
