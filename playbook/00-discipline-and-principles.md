---
layer: L3
scope: project-wide
type: playbook
applies-to: backend
last-updated: 2026-05-14
status: active
---

# ADT Disiplini, Hızlı Erişim ve Genel Prensipler

## 🚨 ZORUNLU DİSİPLİN — ADT İşine Başlamadan Önce

ADT üzerinden herhangi bir obje (Domain, DTEL, Table, CDS, Message Class, Function Group, Lock Object, Behavior Definition, Access Control, vb.) yaratırken / güncellerken / silerken **SIRASIYLA** şu adımları izle:

### 1️⃣ Önce: Bu Playbook'u Tara

İlgili işin **bu playbookda var mı** kontrol et:
- Bölüm başlıklarını oku (`## N. Konu Adı`)
- `## ⚡ HIZLI ERİŞİM` tablosu hızlı index sunar
- İlgili bölüm varsa **adım adım uygula**

### 2️⃣ Playbookda Yoksa veya Çalışmıyorsa: Referans Script'lerini İncele

📂 **`<PROJECT_ROOT>\scripts\`** klasörü = NTT abaper plugin'in tam kopyası (59 Python dosyası).

Bu klasör **ADT REST endpoint'lerinin nasıl çağrılacağını gösteren çalışan örneklerle dolu**. Bir işte takılırsan:

1. **Konuya uygun script'i bul** (`ls scripts/ | grep <konu>`)
   - Örnek: Table yaratma → `create_table.py`
   - Örnek: CDS view → `create_cds_view.py`
   - Örnek: Function module → `create_function_module.py`
   - Örnek: Lock object → `create_lock_object.py`
   - Örnek: Access control → `create_access_control.py`
   - Genel push işlemleri → `push_object.py`
   - Domain/DTEL/Structure/Type group → `create_*.py`
   - Genel kütüphane → `sap_adt_lib.py`, `sap_client.py`
2. **Script'i oku** — endpoint, headers, body XML şemasını gör
3. **Pattern'i uyarlayıp test et**
4. **Çalışırsa playbook'a yeni bölüm olarak ekle** (gelecekte tekrar uğraşmamak için)

### 3️⃣ Hiçbiri Çalışmıyorsa: Kullanıcıya Sor

Üst üste 3-5 başarısız denemeden sonra **dur ve kullanıcıya rapor et**. Aklı evvel deneme yapma — kullanıcıya ne denediğini ve nerede takıldığını net anlat.

### 4️⃣ Başardıktan Sonra: Playbook'u Güncelle

Çözülen her yeni sorun **mutlaka playbook'a yazılır**. Aksi takdirde aynı saat boşa gider. Format:
- Bölüm: `## N. Konu Adı — Çalışan Pattern`
- İçerik: Adım adım kod, kritik header/param/XML notları, başarısız yolların kısa arşivi.

> **⚠️ Hatırla:** Bu disiplin Sprint 0.1'de mesaj sınıfı sorununu çözmemize yaradı. 50+ varyant denedik ama doğru kaynağı (kütüphanedeki `create_message_class.py`) incelemeden çözüm bulamadık. Bundan sonra ilk gün scripts/ klasörünü incelemekle başla.

### 5️⃣ TD Namespace WHITELIST — POZİTİF KURAL (Sprint 3 + Sprint 4 Hataları)

ZSD001 modülünde **tek geçerli format** vardır. Whitelist'te olmayan her şey YASAK. Negatif ifade ("X olmasın") yetmez — pozitif ifade ("**Y OLMALI**") kullan.

**WHITELIST (üç katmanlı zorunluluk):**

| Katman | TEK GEÇERLİ FORMAT | Regex |
|---|---|---|
| 1. CDS `@AbapCatalog.sqlViewName` | **`ZSD001_V_<1-5 char>`** (≤14 toplam) | `^ZSD001_V_[A-Z0-9]{1,5}$` |
| 2. CDS `define view <name>` | **`zsd001_ddl_<x>`** | `^zsd001_ddl_[a-z0-9_]+$` |
| 3. Source body referansları | Sadece `zsd001_*` (Z-CDS/tablo/DTEL) | (hiç `zsd_007_*` veya `'ZSD01XXXX'` yok) |

**Geçmiş hatalar (referans):**

| Hata | Sebep | Etki |
|---|---|---|
| Sprint 3: `_convert_cds_sources.py` manuel dictionary | Bazı entry eksik kaldı | 8+ CDS `ZSD_007_CV_*` ile aktive oldu, TADIR cleanup |
| Sprint 3: bazı CDS'ler `ZSD15XXXX` kısaltma ile aktive | Eski stil syntax | TADIR orphan, rename broken |
| Sprint 4 (2026-05-13): SHIPPING_TYPES rename hatası | TADIR'da `ZSD15SHTYP` orphan | Aktivasyon başarısız |

**ASLA:**
- ❌ Elle dictionary map: `{'X': 'Y', ...}` — entry UNUTULUR
- ❌ Negatif kontrol: "ZSD_007_* olmasın" — `ZSD15XXXX` bypass eder

**HER ZAMAN:**
- ✅ Whitelist regex: `^ZSD001_V_[A-Z0-9]{1,5}$` — tek format
- ✅ Toplu regex dönüşümü: `re.sub(r"'ZSD_007_(?:CV|V)_(\w+)'", lambda m: f"'ZSD001_V_{m.group(1)[:5]}'", src)`

**Kod düzeyi kontrol (mecburi, otomatik):**

`scripts/populate_cds_views.py` → `validate_sql_view_names()` fonksiyonu **3 katmanı da** doğrular. Her `.cds` dosyasında:
1. sqlViewName whitelist regex'e uygun mu?
2. define view name whitelist regex'e uygun mu?
3. Source body içinde yasak literal var mı (`zsd_007_*`, `'ZSD007_CV_*'`, `'ZSD01XXXX'`)?

Tek bir ihlal varsa **script HEMEN exit 1**, hiçbir POST/PUT/aktivasyon yapılmaz.

**Manual kontrol komutları (script'i baypas etmek için her şeyden önce çalıştır):**
```powershell
# 1. sqlViewName whitelist dışı (BOŞ çıkmalı)
grep -EL "^@AbapCatalog\.sqlViewName:\s*'ZSD001_V_[A-Z0-9]{1,5}'" ERP/<paket>/TD/cds_src/*.cds

# 2. view name whitelist dışı (BOŞ çıkmalı)
grep -EL "^define view zsd001_ddl_" ERP/<paket>/TD/cds_src/*.cds

# 3. Source body'de yasak referans (BOŞ çıkmalı)
grep -nE "(zsd_007_|'ZSD_007_(CV|V)_|'ZSD[0-9]{2}[A-Z]{4,8}')" ERP/<paket>/TD/cds_src/*.cds
```

> **⚠️ Bu kuralı atlamak = TADIR cleanup + transport release = saatler kaybı.**
> Sprint 3'te 2 kez, Sprint 4'te SHIPPING_TYPES vakasında bir kez daha bu hatayı yaşadık. Pre-flight check artık aktif — bypass etmek imkansız.

### 6️⃣ TD Spec Disiplini — TÜM Obje Tipleri İçin (Sprint 4 Hatası — 2026-05-13)

**Yeni obje yarat/değiştir/sil işleminde TD spec TEK karar otoritesi.** <LEGACY_SOURCE> source sadece **structural pattern** referansı.

**Geçerli obje tipleri:** CDS, Class, Program, Structure, Table, Auth (`TD/<folder>/` altında MD spec)

#### Akış (her obje için):

```
1. TD spec'i ara:
   - <module>/TD/<folder>/<NAME>.md          ← öncelik (TD karar)
   - <module>/<LEGACY_MODULE>/<folder>/<NAME>.md    ← fallback (<LEGACY_SOURCE>)

2. TD spec VARSA:
   ✅ Tüm "Silinen Alanlar / Kaldırılan Join / ❌" kararları UYGULANIR
   ✅ Korunan listesi haricinde HİÇBİR alan eklenmez
   ✅ <LEGACY_SOURCE> source sadece JOIN topology + calc formül desenleri için
      bakılabilir, ALAN listesi/business logic kararları için DEĞİL

3. TD spec YOKSA:
   ❌ STOP — <LEGACY_SOURCE>'a otomatik fallback YASAK
   ✅ Operatöre rapor: "<NAME> için TD spec yok. <LEGACY_SOURCE>'da X referansı var.
      <LEGACY_SOURCE>'ı fallback alabilir miyim? Onay ver."
   ✅ Onay alınmadan obje yaratılmaz/değiştirilmez.
```

#### Sprint 4 Hatası (referans)

CDS yaratımında <LEGACY_SOURCE> source'undan TD'ye **direkt namespace dönüşümü** yaptım, TD spec'in "Silinen Alanlar" tablosunu **okumadan**. Sonuç:
- ZSD001_S_EXAMPLE_IT: 15 silinmesi gereken alan source'ta kaldı → aktivasyon fail
- ORDER_ITEMS_SO/SA: 3 alan + 2 join silinmesi gereken kaldı → audit gerekti
- ZSD001_DDL_EXAMPLE_LIST: `WHERE LIKE '77%'` filtresi kaldırılmamış kaldı

**Kök sebep:** <LEGACY_SOURCE> ham kaynaktan başladım, TD karar dokümanını atladım. Spec'ler tasarım kararlarını içerir (silinen feature'lar, K13 kararı, vs.) — ham kaynak değil **spec** karar otoritesidir.

#### Kod düzeyi kontrol (otomatik, bypass edilemez)

**Helper:** `scripts/td_spec_check.py`
- `require_td_spec(name, type)` → spec yoksa `exit 1` (operator approval mesajı)
- `find_deleted_items(spec_text)` → "Silinen Alanlar/Kaldırılan" tablolarını parse eder
- `scan_source_for_deleted(source, deleted)` → source'ta varsa raporlar

**Entegrasyon:**
- ✅ `populate_cds_views.py` pre-flight katman 2 olarak entegre edildi (Sprint 4)
- ⏳ `populate_tables.py`, `populate_structures.py`, gelecek populate script'leri aynı pattern'i kullanır
- ⏳ TempScripts converter'lar (<LEGACY_SOURCE> → TD dönüşüm) zorunlu çağırır: `require_td_spec(name, type)` ilk satır

#### Manuel kontrol (script bypass etmek istiyorsan)

```powershell
# CDS spec check CLI
python scripts/td_spec_check.py ZSD001_DDL_ORDER_ITEMS cds ERP/SD/ZSD001_CLC/cds/ZSD001_DDL_ORDER_ITEMS.cds
```

> **⚠️ Bu kuralı atlamak = Spec'te silinen feature'ları geri getirme = production'da yanlış davranış.** Sprint 4'te 4 CDS için audit + düzeltme gerekti.

---

## ⚡ HIZLI ERİŞİM — Çözülmüş Sorunlar

| Sorun | Bölüm | Anahtar Çözüm |
|---|---|---|
| **Mesaj sınıfı (MSAG) içine REST ile mesaj yazma** | Bölüm 18 | `If-Match` header'ını gönderME, try/finally + UNLOCK |
| Domain + DTEL yaratma (TR labels) | Bölüm 14 | `responsible`, `abapLanguageVersion`, `language` attributes ŞART |
| DTEL update (label değiştirme) | Bölüm 14.5 | DELETE + tekrar CREATE (PUT bu sistemde broken) |
| **Built-in DTEL (DATS/INT2/TIMS)** | Bölüm 14.6 | `typeKind=domain` + `typeName=DATS/INT2/...` (BUILTIN type kind YOK) |
| **Batch Domain yaratma (CSV-driven)** | Bölüm 14.1 | `scripts/populate_domains.py` |
| **Batch DTEL yaratma (CSV-driven)** | Bölüm 14.2 + 14.6 | `scripts/populate_dataelements.py` |
| **Z Tablo (TABL/DT) yaratma** | Bölüm 15 | POST shell + PUT /source/main (If-Match GÖNDERME), `scripts/populate_tables.py` |
| **Lock Object (ENQU/DL) yaratma** | Bölüm 16 | URL `/lockobjects/sources/{name}` (sources alt yolu), `scripts/populate_lock_objects.py` |
| **CDS View (DDLS/DF) yaratma** | Bölüm 17 | 2-step POST shell + LOCK + PUT source/main + UNLOCK (table pattern), `scripts/populate_cds_views.py` |
| **TD Namespace WHITELIST (sqlViewName + view name + source body)** | Bölüm 17.9 + §1.5 | POZİTİF KURAL: `'ZSD001_V_<≤5>'` + `zsd001_ddl_<x>` + body'de hiç `zsd_007_*` / `'ZSD01XXXX'` yok. Pre-flight `populate_cds_views.py::validate_sql_view_names()` 3 katmanı denetler, ihlal=exit 1 |
| **TD Spec Disiplini (tüm obje tipleri)** | §1.6 | TD spec TEK karar otoritesi. <LEGACY_SOURCE> sadece structural pattern. Spec'te "Silinen" varsa source'ta olmamalı. Spec yoksa **operator approval** şart. Helper: `scripts/td_spec_check.py` — populate scripts ilk satırda çağırır, ihlal=exit 1 |
| **`@AbapCatalog.preserveKey` deprecated** | Bölüm 17 | S/4'te uyarı verir, kaldır |
| **Quantity → Unit / Currency → Para Birimi referansı (DDL annotation)** | Bölüm 15.3 | Quantity: `@Semantics.quantity.unitOfMeasure : 'TABLE.UNIT'` / Currency: `@Semantics.amount.currencyCode : 'TABLE.WAERS'` (qualified format ŞART) |
| **`@AbapCatalog.enhancement.category` zorunlu** | Bölüm 15.3 | `#NOT_EXTENSIBLE` — yoksa "Can't save due to errors" |

---

## GENEL KODLAMA KURALLARI

- **`CHECK sy-subrc = 0.` KULLANMA** — yerine her zaman `IF sy-subrc = 0. ... ENDIF.` bloğu kullan.
- **TCURR direkt kullanma** — kur dönüşümü için `I_ExchangeRate` CDS kullan (bkz. Bölüm 25).
- **ALV Hotspot ile Transaction Açma:** `SET PARAMETER ID` + `CALL TRANSACTION '...' AND SKIP FIRST SCREEN` kullan. Transaction kapanınca rapor geri gelir.
  - VA33 (Teslimat Planı görüntüle) → Parametre ID: `LPN`, alan: `vbeln`
  - VA03 (Satış Siparişi görüntüle) → Parametre ID: `AUN`, alan: `vbeln`

---

## ABAP EXPERT KODLAMA PRENSİPLERİ

### 1. İç Tablo Initialization — Loop İçinde INSERT Yapma
Sonuç tablosu (`lt_tutar` gibi) başta belli olan veriden türetiliyorsa loop dışında `VALUE #( FOR ... )` ile initialize et. Loop içinde READ+INSERT+READ pattern'i hem yavaş hem okunaksız.
```abap
lt_tutar = VALUE #( FOR <b> IN lt_baglanti
  ( fiyat_kodu = <b>-fiyat_kodu  para_birimi = <b>-para_birimi ) ).
```
Sonra loop içinde sadece `ASSIGN ... TO <t>` + `IF <t> IS ASSIGNED` kullan. FIELD-SYMBOL'ü DATA bloğunda tanımla, inline `FIELD-SYMBOL(<x>)` aynı scope'ta iki kez kullanılamaz.

### 2. SQL'de Hesapla, ABAP'ta Döngü Kurma
Aggregation ve aritmetik mümkünse SQL'de yap:
- Toplam miktar: `SUM( lfimg ) GROUP BY vgbel, vgpos` — ayrı ABAP loop yok
- Vergi dahil tutar: `vbap~netwr + vbap~mwsbp AS brutto` — loop içinde toplama yok
- JOIN zinciri: LIPS+VBAP JOIN → birim fiyat direkt gelir, ayrı READ TABLE yok

### 3. WHERE Koşulları — Sabit Değerleri Range Değişkenine Al
Inline sabit `NOT IN ( 'X', 'Y' )` yazmak hem okunaksız hem bakımı zor. Her zaman range değişkeni tanımla:
```abap
lt_blart_exc = VALUE #( ( sign='E' option='EQ' low='XX' ) ( sign='E' option='EQ' low='YY' ) ).
...
AND bkpf~blart IN @lt_blart_exc
```
Aynı range birden fazla SELECT'te kullanılabilir, iş kuralı değişince tek yerden güncellenir.

---

## BAĞLANTI BİLGİLERİ

```
Host    : <SYSTEM_ID>.SAP.EXAMPLE.COM.TR
Port    : 44300
Client  : 100
User    : <SAP_USER>
Config  : <PROJECT_ROOT>\.conn_adt
```

Script çalıştırma base komutu:
```powershell
python <script_path> --conn <PROJECT_ROOT>\.conn_adt
```

---


