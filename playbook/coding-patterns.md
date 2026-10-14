---
applies_to: [s4_private]
layer: L3
scope: project-wide
type: playbook
applies-to: backend
last-updated: 2026-05-14
status: active
---

# ABAP Coding Patterns — Range, FOR ALL ENTRIES, İç Tablo, Kur Dönüşümü

## 22. Range Parametresi Kuralları

### Kural: Method parametresi olarak RANGE OF kullanılamaz — her zaman TABLE TYPE kullan

SAP ABAP'ta method/function IMPORTING/EXPORTING/CHANGING parametresinde `TYPE RANGE OF xyz` yazamazsın.
`RANGE OF` sadece yerel `DATA` tanımında geçerli. Method imzasında kullanılırsa aktivasyon hatası alırsın.

> **Aile:** method-imza save-scan ailesinin konsolide evi → [`adt-classes.md`](adt-classes.md) §24.6; bu §22 = RANGE OF parametre derin-reçetesi (Yol A/B).

**Çözüm — alana göre iki farklı yol:**

#### Yol A: Standart SAP alanı → Operatörden mevcut table type'ı sor

Standart bir alan için range table type'ı zaten SAP'ta vardır ama adını bilmiyorsun.
Bu durumda **operatörden sor** — SE11'de ilgili data element'in `Where-Used` listesine bakarak veya
bildiği ismi vererek doğru table type adını öğren.

Bilinen örnekler (bu projede doğrulanmış):
| Alan | Data Element | Table Type | Row Type |
|------|-------------|------------|----------|
| `vkorg` | `VKORG` | `SD_VKORG_RANGES` | `SDSLS_VKORG_RANGE` |
| `kunnr` | `KUNNR` | `SHP_KUNNR_RANGE_T` | `SHP_KUNNR_RANGE` |
| `budat` | `BUDAT` | `TDT_RG_BUDAT` | `TDS_RG_BUDAT` |

#### Yol B: Z'li (custom) alan → Structure + Table Type kendin yarat

Eğer alan `ZZ1_...` veya `Z...` gibi custom bir data element ise SAP'ta hazır range table type yoktur.
O zaman **kendin DDIC'te yarat:**

1. **Structure** yarat (örn. `ZSD001_S_SEL_PRICE`):
   - `SIGN`   TYPE `DDSIGN`
   - `OPTION` TYPE `DDOPTION`
   - `LOW`    TYPE `<custom_data_element>`
   - `HIGH`   TYPE `<custom_data_element>`

2. **Table Type** yarat (örn. `ZSD001_TT_SEL_PRICE`):
   - Row Type = yukarıdaki structure
   - Table Kind = Standard

3. Method imzasında bu table type'ı kullan:
```abap
METHODS constructor
  IMPORTING
    it_fiyat_listesi TYPE zsd001_tt_sel_price.  " DOGRU
"   it_fiyat_listesi TYPE RANGE OF zz1_price_code.  " YANLIS — aktivasyon hatası
```

### Özet

| Durum | Yapılacak |
|-------|-----------|
| Standart SAP alanı için range | Operatörden table type adını sor, SE11'de doğrulat |
| Custom Z alanı için range | SE11'de structure + table type yarat, sonra kullan |
| Yerel metod içi range (parametre değil) | `DATA lt TYPE RANGE OF xyz.` — sorunsuz çalışır |

---

## 23. FOR ALL ENTRIES + GROUP BY Yasağı

### Kural: `FOR ALL ENTRIES` ve `GROUP BY` aynı SELECT'te kullanılamaz

SAP ABAP'ta `FOR ALL ENTRIES IN lt_tablo` ile birlikte `GROUP BY` yazamazsın — syntax hatası alırsın.
Bu kombinasyona ihtiyaç duyduğunda iki alternatif vardır:

---

### Yol A: `INNER JOIN @itab` (önerilen)

İç tabloyu doğrudan FROM clause'a join et. S/4HANA 1909+ destekler.
Zorunlu pragma'ları eklemeyi unutma:

```abap
TYPES: BEGIN OF ty_filter,
         siparis_no TYPE vbeln,
         kalem_no   TYPE posnr,
       END OF ty_filter.
DATA lt_filter TYPE HASHED TABLE OF ty_filter WITH UNIQUE KEY siparis_no kalem_no.

" lt_filter'ı doldur
lt_filter = VALUE #( FOR ls IN mt_siparisler ( siparis_no = ls-siparis_no kalem_no = ls-kalem_no ) ).

SELECT l~vgbel AS siparis_no,
       l~vgpos AS kalem_no,
       SUM( l~lfimg ) AS toplam_mik
  FROM lips AS l
  INNER JOIN @lt_filter AS fil
    ON  fil~siparis_no = l~vgbel
    AND fil~kalem_no   = l~vgpos
  GROUP BY l~vgbel, l~vgpos
  INTO TABLE @DATA(lt_sonuc)
  ##db_feature_mode[itabs_in_from_clause] ##itab_db_select.
```

**Dikkat:**
- `##db_feature_mode[itabs_in_from_clause]` ve `##itab_db_select` pragmaları **zorunlu** — eksik olursa syntax/warning hatası
- Join edilen iç tablo HASHED veya SORTED olmalı (performans için)
- Bu yöntem büyük iç tablolarda da verimli çalışır

---

### Yol B: Raw rows çek, ABAP'ta topla

`GROUP BY` yerine ham satırları çekip ABAP'ta `LOOP` + `ASSIGN` ile toplama yap.
Özellikle CDS alanı CURR(34,2) gibi büyük tipli ise `SUM` hedef tipe sığmayacağından bu yöntem zorunlu olur (bkz. Bölüm 25.3).

```abap
" SQL'de sadece filtre + raw rows
SELECT musteri_no, borc_alacak_kodu, tutar
  FROM i_operationalacctgdocitem
  INTO TABLE @lt_raw
  WHERE ...

" ABAP'ta grupla
LOOP AT lt_raw INTO ls_row.
  ASSIGN ht_ozet[ musteri_no = ls_row-musteri_no ] TO FIELD-SYMBOL(<acc>).
  IF <acc> IS NOT ASSIGNED.
    INSERT VALUE #( musteri_no = ls_row-musteri_no ) INTO TABLE ht_ozet ASSIGNING <acc>.
  ENDIF.
  " toplama mantığı...
  UNASSIGN <acc>.
ENDLOOP.
```

---

### Karar tablosu

| Durum | Yöntem |
|-------|--------|
| `FOR ALL ENTRIES` + `GROUP BY` gerekiyor | Yol A: `INNER JOIN @itab` + pragma |
| Hedef alan tipi küçük (wrbtr, kwmeng) | Yol A tercih edilir |
| Hedef alan tipi büyük (CURR 34,2 gibi) | Yol B zorunlu — SUM sığmaz |
| İç tablo çok büyük (100k+ satır) | Yol B daha güvenli |

---

## 24. İç Tablo Boş Kontrolü — SELECT Öncesi

### Kural: İç tablo kullanılan her SELECT'ten önce boş kontrolü yap

Bu kural iki farklı kullanım için geçerlidir:

#### 28.1 `FOR ALL ENTRIES IN lt_tablo`

`lt_tablo` boşsa SAP **tüm tabloyu çeker** — WHERE koşulu yok sayılır, full table scan olur.
Hem performans felaketi hem yanlış veri döner.

```abap
" YANLIS — boş kontrol yok:
SELECT matnr, netpr
  FROM a004
  FOR ALL ENTRIES IN lt_musteriler
  WHERE kunnr = lt_musteriler-kunnr
  INTO TABLE @lt_fiyat.

" DOGRU:
IF lt_musteriler IS NOT INITIAL.
  SELECT matnr, netpr
    FROM a004
    FOR ALL ENTRIES IN lt_musteriler
    WHERE kunnr = lt_musteriler-kunnr
    INTO TABLE @lt_fiyat.
ENDIF.
```

#### 28.2 `INNER JOIN @lt_itab` (FROM clause'da iç tablo)

`lt_itab` boşsa join sonucu zaten boş döner — veri riski yok.
Ama gereksiz DB round-trip önlemek için yine de kontrol önerilir.

```abap
IF lt_filter IS NOT INITIAL.
  SELECT ...
    FROM lips AS l
    INNER JOIN @lt_filter AS fil ON ...
    INTO TABLE @lt_sonuc
    ##db_feature_mode[itabs_in_from_clause] ##itab_db_select.
ENDIF.
```

### Özet — Genel Kural

> **`FOR ALL ENTRIES IN lt_tablo` kullanımından önce `IF lt_xxx IS NOT INITIAL` kontrolü zorunludur — iç tablo ne olursa olsun (range, sipariş listesi, müşteri listesi, her şey).**
>
> Sebep: SAP `FOR ALL ENTRIES` ifadesinde iç tablo boşsa WHERE koşulunu yok sayar ve **tüm tabloyu çeker**. Bu hem performans felaketi hem yanlış veri demektir.
>
> `WHERE ... IN @lt_range` ise farklıdır — range boşsa SAP "kriter yok, hepsi isteniyor" yorumlar ve full çeker, bu **beklenen davranıştır**, tehlikeli değildir.
>
> `INNER JOIN @lt_itab` boşsa sonuç zaten boş döner — veri riski yok ama gereksiz DB çağrısını önlemek için kontrol önerilir.

---

## 25. Kur Dönüşümü — I_ExchangeRate CDS

### Sorun

`TCURR` tablosunu direkt kullanmak güvenilmez:
- `GDATU` alanı `CHAR(8)` ters tarih formatı (`99999999 - YYYYMMDD`) — ABAP'ta tip ataması ve karşılaştırma sorunları çıkar
- `FFACT / TFACT` sıfır olabilir → sıfıra bölme hatası
- `UKURS` tek başına yeterli değil, `FFACT/TFACT` ile formül gerekir

### Çözüm: I_ExchangeRate CDS

SAP standart `I_ExchangeRate` CDS view'ı tüm bu karmaşıklığı çözüyor:
- `ExchangeRateEffectiveDate` → düz `YYYYMMDD` (TYPE d ile doğrudan karşılaştırılabilir)
- `EffectiveExchangeRate` → hazır hesaplanmış efektif kur, formül gerekmez

### Doğru ABAP Kodu

```abap
SELECT SourceCurrency        AS fcurr,
       TargetCurrency        AS tcurr,
       EffectiveExchangeRate AS exchrate
  FROM I_ExchangeRate AS er
  INTO TABLE @lt_kur
  WHERE er~ExchangeRateType = 'M'
    AND er~SourceCurrency IN @lt_all_waers
    AND er~TargetCurrency IN @lt_target_waers
    AND er~ExchangeRateEffectiveDate =
          ( SELECT MAX( e2~ExchangeRateEffectiveDate )
              FROM I_ExchangeRate AS e2
             WHERE e2~ExchangeRateType          = er~ExchangeRateType
               AND e2~SourceCurrency            = er~SourceCurrency
               AND e2~TargetCurrency            = er~TargetCurrency
               AND e2~ExchangeRateEffectiveDate <= @sy-datum ).
```

Kur uygulaması:
```abap
IF sy-subrc = 0 AND <kur>-exchrate <> 0.
  lv_amount = lv_kaynak * <kur>-exchrate.
ENDIF.
```

### Kesin Kurallar

- **TCURR'u direkt ABAP'ta KULLANMA** — `I_ExchangeRate` CDS kullan
- `ExchangeRateType = 'M'` — standart ortalama kur tipi
- Guard ekle: `IF lt_all_waers IS NOT INITIAL AND lt_target_waers IS NOT INITIAL` — boş range ile SELECT yapma

---

## 26. Harici HTTP/REST istemcisi — istek gövdesi UTF-8 BAYT olarak gönderilir (2026-10-12)

> **Kapsam:** ABAP'tan **sistem dışı** bir REST uca (`cl_http_client` / `if_web_http_client`) JSON/XML
> gövde gönderen kod. SAP-içi OData çağrısı bu bölümün konusu değildir — onun kanonik yolu `adt-rap.md` §34.

**Kural:** gövde metin olarak `set_cdata` ile değil, açıkça UTF-8'e çevrilip **bayt** olarak
(`set_data`) verilir ve `Content-Type` başlığı `charset=utf-8` taşır:

```abap
DATA(lv_xbody) = cl_abap_codepage=>convert_to( source = lv_json codepage = `UTF-8` ).
lo_request->set_data( lv_xbody ).
lo_request->set_header_field( i_name = 'Content-Type' i_value = 'application/json; charset=utf-8' ).
```

**Neden:** metin gövdede dönüşüm sistemin/bağlantının kod sayfasına bırakılır; Türkçe karakterler
(`ş ğ ı İ ç ö ü`) karşı tarafta bozuk ya da `?` olarak görünebilir ve hata vermez.
**Kanıt düzeyi:** dış kaynak bildirimi (2026-10-12) — bu evde harici REST çağrısında bozulma **ölçülmedi**
(**DOĞRULANMADI**). İlk harici REST işinde bir Türkçe karakterli gövdeyle karşı tarafta okunarak teyit et.
Komşu: `howto-abap-email.md` (mail gövdesinde aynı dönüşüm ailesi).

---

## 27. Türkçe metin, mesaj değişkeni ve büyük dizgede regex — ÖLÇÜLMÜŞ sınırlar (2026-10-12)

> **Kanıt düzeyi:** S/4HANA on-premise, geliştirme sistemi, classrun, taze süreç; 2026-10-12'de ölçüldü.
> Başka sürüm/profilde yeniden ölçülmeden genellenmez.

### 27.1 `to_upper` / `to_lower` / `TRANSLATE` Türkçe harf kuralına UYMAZ

| girdi | `to_upper` | `to_lower` | `TRANSLATE … TO UPPER CASE` | `TRANSLATE … TO LOWER CASE` |
|---|---|---|---|---|
| `i` | `I` | `i` | `I` | `i` |
| `ı` | `I` | `ı` | `I` | `ı` |
| `İ` | `İ` | `i` | `İ` | `i` |
| `I` | `I` | `i` | `I` | `i` |

- Sonuç oturum dili Türkçeyken, `SET LOCALE LANGUAGE 'E'` sonrasında ve Türkçeye dönüşte **birebir aynı**
  ⇒ dönüşüm metin ortamı diline **bağlı değil**; `to_upper` ile `TRANSLATE` aynı sonucu verir.
- **Pratik sonuç:** Türkçe metni büyük harfe çevirip karşılaştırmak `istanbul` ↔ `İSTANBUL` eşleşmesini
  **kaçırır** (`i`→`I` olur, `İ` olduğu gibi kalır). Büyük/küçük harf duyarsız karşılaştırma gerekiyorsa iki
  tarafı aynı fonksiyonla çevirmek yetmez; `İ/I/ı/i` dörtlüsü ayrıca normalize edilir (ör. dördünü tek bir
  temsilciye eşleyen `TRANSLATE … USING`). Yukarıdaki dönüşüm tablosu classrun ölçümüyle doğrulandı
  (2026-10-12); önerilen normalizasyon eşlemesi ise **ölçülmedi** — kullanmadan önce aynı yolla doğrula.
- ⚠ `SET LOCALE LANGUAGE` `sy-langu`'yu da değiştirir — denemeden sonra geri al.
- Kardeş (OData/UI tarafı harf sınıfı): `standards/03` ve FE kontrol listesindeki Türkçe arama notları.

### 27.2 `CONV syst_msgv( … )` uzun metni SESSİZCE keser

`CONV syst_msgv( lx->get_text( ) )` — 119 karakterlik istisna metni **50 karaktere** kesildi; istisna
yok, uyarı yok. Mesaj değişkenine (`&1..&4`) uzun metin taşınacaksa ya parçalara bölünür (`msgv1..msgv4`)
ya da metin başka bir kanalla (uygulama günlüğü, uzun metin) taşınır. Kesildiği varsayılarak ekranda
yarım cümle kalmaması için mesaj envanterinde (std 04 TS 10.1) yer tutucunun en çok 50 karakter taşıdığı yazılır.

### 27.3 `FIND REGEX … SUBMATCHES` büyük dizgede — sınır BOYUTA değil DESENE bağlı

20 055 ve 40 043 karakterlik JSON, aranan alan dizgenin **sonunda**, 5 desen:

| Desen | POSIX (`FIND REGEX`) | PCRE (`FIND PCRE`) |
|---|---|---|
| `"alan":"([^"]*)"` | 40k geçti | 40k geçti |
| `.*"alan":"([^"]*)"` | 40k geçti | 40k geçti |
| `^\{.*"alan":"(.*)"\}$` | 40k geçti | 40k geçti |
| `(?:.\|\n)*"alan":"([^"]*)"` | 40k geçti | 20k geçti · **40k `CX_SY_REGEX_TOO_COMPLEX`** |
| `\{.*?…` (tembel niceleyici; desenin tamamı bu sayfaya aktarılmadı) | **`CX_SY_INVALID_REGEX`** (POSIX'te tembel niceleyici yok) | geçti (hangi boyut(lar)da — bildirilmedi, DOĞRULANAMADI) |

- Dış bir kaynağın bildirdiği sabit "32 KB sınırı" bu 5 desende **doğrulanmadı**; sorun çıkaran,
  alternasyonlu tüm-dizge niceleyicisidir. Yalnız bu 5 desen ölçüldü — başka desenler için hüküm yoktur.
- `FIND REGEX` (POSIX) aktivasyonda uyarı verir: *"The regex standard POSIX is deprecated"* ⇒ yeni kodda PCRE.
- Büyük dizgede tek alan aranıyorsa en basit bağlamlı desen (`"alan":"([^"]*)"`) yeğlenir; JSON
  ayrıştırması gerekiyorsa regex yerine JSON ayrıştırıcısı (`/ui2/cl_json` ya da sürümün released ayrıştırıcısı —
  released durumu **DOĞRULANMADI**) düşünülür.
