---
applies_to: [s4_private]
layer: L2
scope: project-wide
applies-to: fs-ts-kd
version: 1.2
last-updated: 2026-07-11
status: active
---

<!-- v1.2 (2026-07-11): FS §2.0 kullanıcı-gözü + öneri/soru disiplini (İLKE-1/2) + §11-A/11-B;
     TS §3.0 developer-gözü + FS-otoritesi + FS-denetimi + ertelenebilir-ayrımı (İLKE-3/4/5) +
     §2-A/§11-A; §7/§8 checklist+hata güncellendi. Kök ders: bir TS'te fonksiyonel kararların
     (eşleştirme/dönüşüm/UoM) "build'de netleşir"e ertelenmesi → developer tahmine düşer. -->


# SAP Geliştirme Dökümantasyon Kuralları
## Fonksiyonel Spesifikasyon (FS), Teknik Spesifikasyon (TS) ve Kullanıcı Dökümanı (KD) Hazırlama Rehberi

> **Versiyon:** 1.0  
> **Hazırlayan:** OpenCode SAP Expert  
> **Tarih:** 2026-05-05  

---

# BÖLÜM 1: GENEL KURALLAR VE PRENSİPLER

## 1.1 Döküman Hiyerarşisi

```
İş Gereksinimi (Business Requirement)
        ↓
Fonksiyonel Spesifikasyon - FS  (Müşteri/Key User ↔ Danışman; "NE / NEDEN")
        ↓
Teknik Spesifikasyon - TS       (Modül Danışmanı → Developer; "NASIL")
        ↓
Geliştirme / Uygulama
        ↓
Test & UAT
        ↓
Kullanıcı Dökümanı - KD          (Danışman/Key User → Son Kullanıcı; "NASIL KULLANILIR")
        ↓
Canlıya Alma + Eğitim
```

> **KD ne zaman?** Geliştirme bittikten sonra (UAT sırasında/öncesi) hazırlanır, **canlı geçiş eğitiminde** ve sonrasında son kullanıcının başucu kılavuzu olur. FS/TS *geliştirme için*, KD *kullanım için*tir.

## 1.1.0 Kapsam-orantılı FS derinliği (ITG / ADR 0022)

FS derinliği **işin ITG kapsam-sınıfına** (bkz. [`../playbook/intake-triage.md`](../playbook/intake-triage.md)) orantılıdır — her işe tam FS dayatmak (hız) da, kapsamlı işi FS'siz başlatmak (kalite) da hatalıdır:

| Kapsam | FS beklentisi |
|---|---|
| **S0 · nokta-düzeltme** | FS YOK — tek satır "ne değişti + neden" (commit mesajı yeter). |
| **S1 · lokalize** | HAFİF FS — etkilenen alan/ekran + kabul kriteri + varsa risk (yarım sayfa). |
| **S2 · kapsamlı** | TAM FS — intake-artefaktı (ITG şeması) + **EARS** kabul kriterleri ("kullanıcı VA01'de kaydettiğinde sistem X yapmalı" / "miktar kapasiteyi aşarsa uyar") + **INVEST/Definition-of-Ready** (her gereksinim test-edilebilir + kabul-kriterli olmadan build YOK) + **backend ve frontend ayrı** DoR bölümleri. Aşağıdaki (BÖLÜM 2+) tam şablon buraya uygulanır. |

> "Geliştirme Tipi" (Report/Enhancement/Interface/Form; §"FS Şablonu") bölüm-dallanması bu
> kapsam-eksenine DİKtir: S2 bir Report da olabilir bir Interface de — kapsam derinliği,
> tip bölümleri belirler. İkisi birlikte uygulanır.

## 1.1.1 Paket doküman yerleşimi — `ref_docs/` (ADR 0013)

Bir paket başka sistemden (eski <LEGACY_SOURCE> / başka SAP / legacy) dönüştürülüyorsa,
**S4'te 1:1 yaratılmayacak** conversion/planlama dokümanları paket kökünü kirletir.
Bu yüzden:

- **Paket kökü = yaşayan/güncel:** gerçek S4 artefaktları (`cds/`, `classes/`, `programs/`,
  `ui/`) + yaşayan governance docs (`SPRINT_PLAN.md`, `SESSION_NOTES.md`, `SPEC.md`,
  `.rules.md`, `00_OVERVIEW.md`).
- **`ref_docs/` = kaynak/dönüşüm + tarihsel referans:** klasik DDL/struct spec'leri, conversion
  program spec'leri, ekran mockup'ları, çıkarım csv'leri, conversion-dönemi FS/farklılık/bağımlılık
  docs. **Spec kaynağıdır**, canlı teslimat değil; `ref_docs/README.md` manifesti provenance +
  durum (ham/superseded/düştü) tutar.

> Yeni paketler `bootstrap_package.py` ile `ref_docs/` + manifest şablonu alır. Detay: ADR 0013.

## 1.2 Temel Farklar: FS vs TS vs KD

| Özellik | FS (Fonksiyonel) | TS (Teknik) | KD (Kullanıcı) |
|---------|-----------------|-------------|----------------|
| **Hedef Kitle** | Müşteri, İş Analistleri, PM | ABAP Developer, Teknik Mimar | **Son kullanıcı** (işlemi yapan operatör) |
| **Hazırlayan** | Müşteri/Key User ↔ Danışman (birlikte) | Modül Danışmanı (developer'a verir) | Danışman / Key User |
| **Dil** | İş dili, teknik olmayan | Teknik, kod odaklı | **Sade/gündelik dil** ("teknik sıfır", terim sözlükte) |
| **İçerik** | NE / NEDEN yapılacak | NASIL yapılacak (teknik) | **NASIL KULLANILIR** (adım adım) |
| **Soru** | "Ne istiyorum?" | "Nasıl kodlarım?" | "Bunu nasıl kullanırım?" |
| **Detay** | İş süreci + ekran şablonu | Kod/DD + DETAYLI ekran tasarımı | Ekran görüntüsü + tıkla/gir/seç adımları |
| **Onaylayan** | Key User / Proje Müdürü | Teknik Lider / Mimar | Key User |
| **Girdi** | İş gereksinimleri, toplantı notları | FS dökümanı | FS + TS + canlı uygulama |
| **Ne zaman** | Geliştirme öncesi | FS sonrası, geliştirme öncesi | **Geliştirme/UAT sonrası, canlı+eğitim için** |

## 1.3 Ekran Görseli İlkesi (FS/TS vs KD — KRİTİK)

> **FS ve TS**, geliştirme **henüz YAZILMAMIŞ gibi** (tasarım-önce zihniyetiyle) hazırlanır → **gerçek ekran görüntüsü KULLANILMAZ**; ekran **mockup + yapısal tablolarla** (alan/buton/grid/etkileşim/servis) TANIMLANIR. Geliştirme bitmiş olsa bile FS/TS'e ham ekran resmi yapıştırmak yanlıştır (tasarım kararını gizler, "neden böyle" kaybolur).
>
> **KD** ise geliştirme **bittikten sonra** yazılır → **gerçek uygulama ekranlarının görüntüsü AYNEN kullanılır** (mockup değil; kullanıcı bu ekranları görecek). Etkili olması için görüntüler **işaretli/numaralı** (ok/daire/callout) olur — ham/açıklamasız değil.
>
> ⭐ **KD EKRAN VERİSİ = MOCK / TEMİZ ÖRNEK (ZORUNLU — tüm dokümanlar):** Gerçek UI kullanılır AMA içindeki **veri temiz/uydurma örnek** olmalı: anlamlı, tutarlı, profesyonel örnek kayıtlar (örn. "İstanbul–Hamburg Seferi", müşteri "Örnek Denizcilik A.Ş."). **Kirli/gerçek backend kaydı YASAK**: test çöpü ("E2E Test", "NR otomatik test", "ADMIN e2e UPDATED"), tutarsız/eksik satır, gerçek müşteri/PII, anlamsız kod yığını. **Yöntem:** canlı backend'e dokunmadan **client-model state injection** (playwright ile OData/JSON modeline temiz satır enjekte et) — bkz. `playbook/howto-kullanici-dokumani-pdf-ekran-goruntulu.md` §A/§D.0. App'in canlı çöp verisini ekrana basmak = EKSİK KD (doc-gate BLOCKER).

---

# BÖLÜM 2: FONKSİYONEL SPESİFİKASYON (FS) DOKÜMANI

## 2.0 FS YAZIM ZİHNİYETİ — "Kullanıcı Gözü" + Öneri/Soru Disiplini (ÖNCE OKU)

> **FS'i, bu uygulamayı *her gün SEN kullanacakmışsın* gibi yaz.** Bölüm yapısını (2.2)
> doldurmak yetmez; bir son-kullanıcının umursayacağı her şeyi düşün: ekranda ne görünür/
> görünmez, hangi alan default gelir, **boş/hatalı/sıfır-kayıt** durumunda ne olur, toplu
> aksiyon var mı, teyit/geri-alma var mı, "**Kaydet'e basınca arka planda ne oluştuğu**"
> kullanıcıya görünür mü, çok kayıtta performans/ergonomi ne olur. Jenerik şablon bunları
> sormaz — **sen sor.**

**İki değişmez ilke (ihlal = eksik FS):**

**İLKE-1 — KULLANICI İSTEĞİ = KANON.** Kullanıcının/Key User'ın **açıkça yazdığı hiçbir
istek atlanamaz, gölgelenemez, sessizce yeniden yorumlanamaz.** Kullanıcının ifadeleri FS'te
**ön planda** durur ve her biri gereksinim listesinde **izlenebilir + karşılanmış** olmalıdır
(hiçbiri "unutulup" düşmez). Danışman katkıları bu isteklerin **etrafında** durur — **yerine
değil**. Bir öneri kullanıcı isteğiyle çelişiyorsa: isteği uygula, çelişkiyi **soru** olarak getir.

**İLKE-2 — ÖNERİ ve SORU, isteği NETLEŞTİRMEK içindir.** Danışmanın eklediği zenginleştirmeler
`[ÖNERİ]` olarak işaretlenir ve **"BÖLÜM 11-A: DANIŞMAN ÖNERİLERİ (onay bekliyor)"**nde toplanır;
onaylanınca ilgili gereksinime taşınır. Kullanıcının yazdığını **onun yönünde** derinleştiren
**paralel sorular** (alternatif + öneri ile) **"BÖLÜM 11-B: AÇIK KARARLAR / SORU SETİ"**ne yazılır.
Sorular tek-tek, bağlam+öneri ile sorulur ([[sorulari-tek-tek-sor-oneriyle]]).

**Soru-seti zorunluluğu:** Danışmanın **karar veremediği** her nokta 11-B'de *seçenekler +
önerilen seçenek* ile durmalıdır. **Hiçbir açık fonksiyonel nokta "geliştirmede/build'de
netleşir"e ERTELENEMEZ** — FS mutabakatı, 11-A boşalıp 11-B'deki her karar kapandığında olur.

**Kullanıcı-gözü tamlık — FS'i bitirmeden kendine sor:**
- Boş dosya / 0 kayıt / mükerrer / çok-fazla (max) kayıtta ekran ne yapar?
- Her alanın default'u, zorunluluğu, "boş bırakırsam ne olur"u yazılı mı?
- Hata nasıl gösterilir (satır mı, toplu mu, birebir metin mi), kullanıcı ne yapacağını biliyor mu?
- İşlem geri alınabilir mi? Teyit isteniyor mu? Yarım-iş kalır mı?
- "Kaydet/İşle" sonrası sistemde **ne oluştuğu** kullanıcıya görünür mü?
- Kullanıcının **yazdığı her istek** gereksinim/kural olarak FS'te var mı (izlenebilir)?

## 2.1 FS Nedir?

Fonksiyonel Spesifikasyon, bir iş gereksiniminin SAP sisteminde **ne şekilde karşılanacağını** iş perspektifinden tanımlayan belgedir. Müşteri ile danışman arasındaki sözleşme niteliğindedir. Müşteri bu belgeyi okuyup anlayabilmeli ve onaylayabilmelidir.

## 2.2 FS Döküman Yapısı (Zorunlu Bölümler)

### KAPAK SAYFASI

```
Döküman Başlığı     : [Geliştirmenin adı - örn. "Satış Siparişi Onay Ekranı"]
Döküman Numarası    : [FS-SD-001]  (modül kodu + sıra no)
Proje Adı           : [Proje adı]
Müşteri             : [Müşteri firma adı]
Hazırlayan          : [Danışman adı - unvanı]
Tarih               : [GG.AA.YYYY]
Versiyon            : [1.0]
Durum               : [Taslak / İncelemede / Onaylandı]
```

---

### BÖLÜM 1: DÖKÜMAN KONTROLÜ

**1.1 Versiyon Geçmişi**

| Versiyon | Tarih | Hazırlayan | Açıklama |
|----------|-------|------------|----------|
| 0.1 | GG.AA.YYYY | Ad Soyad | İlk taslak |
| 1.0 | GG.AA.YYYY | Ad Soyad | Müşteri geri bildirimleri sonrası revize |

**1.2 Dağıtım Listesi**

| Ad Soyad | Ünvan | Rol | E-posta |
|----------|-------|-----|---------|
| ... | Proje Müdürü | Onaylayan | ... |
| ... | Key User | Gözden Geçiren | ... |

**1.3 İlgili Dökümanlar**

| Döküman No | Döküman Adı | Açıklama |
|------------|-------------|----------|
| TS-SD-001 | Teknik Spesifikasyon | Bu FS'e bağlı TS |
| BBP-SD-001 | Business Blueprint | İş süreç dokümantasyonu |

---

### BÖLÜM 2: GİRİŞ VE GENEL BAKIŞ

**2.1 Amaç**

Bu bölümde şunlar yazılır:
- Dökümanın amacı (1-2 paragraf)
- Hangi iş problemini çözdüğü
- Kapsamı ve sınırları

**Örnek:**
> Bu döküman, <PROJECT_NAME> A.Ş.'nin satış siparişi onay sürecini SAP SD modülünde özelleştirme yoluyla otomatize etmek için hazırlanmış fonksiyonel spesifikasyondur. Mevcut manuel onay süreci email üzerinden yürütülmekte olup bu geliştirme ile onay süreci SAP içinde yönetilecektir.

**2.2 Kapsam**

- **Kapsam İÇİNDE olanlar:** Neler dahil
- **Kapsam DIŞINDA olanlar:** Neler dahil değil (çok önemli!)

**2.3 Varsayımlar ve Bağımlılıklar**

- Sistem varsayımları (hangi SAP sürümü, hangi modüller aktif)
- Organizasyonel varsayımlar
- Diğer geliştirmelere bağımlılıklar

**2.4 Referans Dokümanlar**

---

### BÖLÜM 3: İŞ SÜRECİ TANIMI

**3.1 AS-IS Süreci (Mevcut Durum)**

Mevcut iş sürecini adım adım anlatır:
- Süreç akış diyagramı (swimlane diagram tercih edilir)
- Her adımda kimin ne yaptığı
- Kullanılan araçlar/sistemler
- Mevcut sorunlar ve eksiklikler

**Yazım Kuralı:** Her adım numaralandırılır, sorumlu belirtilir.

```
Adım 1: Satış temsilcisi siparişi Excel'e girer
Adım 2: Excel satış müdürüne email ile gönderilir
Adım 3: Satış müdürü emaili inceler ve onaylar/reddeder
Adım 4: Onay emaili satış temsilcisine iletilir
Adım 5: Satış temsilcisi SAP'a sipariş girer
```

**3.2 TO-BE Süreci (Hedef Durum)**

SAP ile nasıl olacağını anlatır:
- Süreç akış diyagramı
- SAP transaction'ları
- Değişen roller ve sorumluluklar
- Beklenen faydalar

**3.3 Gap Analizi**

| # | Mevcut Durum | Hedef Durum | Gap | Çözüm Yöntemi |
|---|-------------|-------------|-----|---------------|
| 1 | Manuel onay email ile | Otomatik SAP workflow | Workflow yok | Custom geliştirme |
| 2 | Excel takibi | SAP raporlama | Rapor yok | ABAP report |

---

### BÖLÜM 4: FONKSİYONEL GEREKSİNİMLER

**4.1 Gereksinim Listesi**

Her gereksinim aşağıdaki formatta yazılır:

| Gereksinim No | Açıklama | Öncelik | Kategori |
|--------------|----------|---------|----------|
| FR-001 | Sistem onay için 2 seviyeli hiyerarşi desteklemelidir | Zorunlu | İş Kuralı |
| FR-002 | Onay bildirimi email ile gönderilmelidir | İstenen | Bildirim |
| FR-003 | Reddedilen siparişler raporlanabilmelidir | Zorunlu | Raporlama |

**Öncelik Kategorileri:**
- **Zorunlu (Must Have):** Olmadan sistem çalışmaz
- **İstenen (Should Have):** Önemli ama olmasa da olur
- **Güzel Olur (Nice to Have):** İleride eklenebilir

**4.2 İş Kuralları**

Her iş kuralı açık, net ve test edilebilir şekilde yazılır:

```
KR-001: Sipariş tutarı 10.000 TL'yi aştığında Satış Müdürü onayı zorunludur.
KR-002: Sipariş tutarı 50.000 TL'yi aştığında Genel Müdür onayı zorunludur.
KR-003: Onay bekleme süresi 48 saati geçerse sistem otomatik uyarı gönderir.
KR-004: Reddedilen sipariş revize edilip tekrar onaya gönderilebilir.
KR-005: İptal edilen sipariş onaya gönderilemez.
```

---

### BÖLÜM 5: KULLANICI ARAYÜZLERİ VE EKRANLAR

**5.1 Ekran Listesi**

| Ekran No | Ekran Adı | Transaction | Açıklama |
|----------|-----------|-------------|----------|
| SCR-001 | Onay Bekleyen Siparişler | ZSD_ONAY | Ana liste ekranı |
| SCR-002 | Sipariş Onay Detayı | ZSD_ONAY_DET | Detay ve onaylama ekranı |

**5.2 Ekran Mockup'ları**

Her ekran için:
- Alan listesi ve açıklamaları
- Zorunlu/opsiyonel alan belirtimi
- Buton/aksiyon tanımları
- Validasyon kuralları

```
EKRAN: ZSD_ONAY - Onay Bekleyen Siparişler
┌─────────────────────────────────────────────────────┐
│  Filtreler                                          │
│  Sipariş No: [________]  Tarih: [____] - [____]    │
│  Müşteri   : [________]  Durum : [Beklemede    ▼]  │
│  [Ara]                                              │
├─────────────────────────────────────────────────────┤
│  Sipariş No │ Müşteri │ Tutar   │ Tarih   │ Durum  │
│  1000000001 │ MÜST001 │ 15.000  │ 01.05   │ Bekle  │
│  1000000002 │ MÜST002 │ 75.000  │ 02.05   │ Bekle  │
├─────────────────────────────────────────────────────┤
│  [Onayla]  [Reddet]  [Detay]  [Geri Dön]           │
└─────────────────────────────────────────────────────┘
```

**Alan Açıklamaları:**

| Alan Adı | Etiket | Tip | Uzunluk | Zorunlu | Açıklama |
|----------|--------|-----|---------|---------|----------|
| VBELN | Sipariş No | Char | 10 | Evet | SAP satış sipariş numarası |
| KUNNR | Müşteri | Char | 10 | Evet | Müşteri kodu |
| NETWR | Tutar | Decimal | 15.2 | Evet | Net sipariş tutarı |

---

### BÖLÜM 6: VERİ GEREKSİNİMLERİ

**6.1 Alan Eşleştirme (Field Mapping)**

Mevcut sistemden SAP'a veri göçü veya entegrasyon durumunda:

| Kaynak Alan | Kaynak Sistem | Hedef Alan | SAP Tablosu | Dönüşüm Kuralı |
|------------|--------------|------------|-------------|----------------|
| ORDER_NO | Excel | VBELN | VBAK | Birebir kopyala |
| CUST_CODE | ERP | KUNNR | KNA1 | Müşteri eşleştirme tablosundan |
| ORDER_DATE | Excel | AUDAT | VBAK | GG/AA/YYYY → YYYYMMDD |

**6.2 Veri Kalitesi Gereksinimleri**

- Zorunlu alanlar
- Format gereksinimleri
- Validasyon kuralları

---

### BÖLÜM 7: ENTEGRASYON GEREKSİNİMLERİ

**7.1 SAP Modül Entegrasyonları**

| Entegrasyon | Kaynak Modül | Hedef Modül | Yön | Açıklama |
|------------|-------------|-------------|-----|----------|
| INT-001 | SD | FI | Otomatik | Sipariş onayında muhasebe kaydı |
| INT-002 | SD | MM | Manuel | Stok kontrolü |

**7.2 Dış Sistem Entegrasyonları**

| Sistem | Entegrasyon Tipi | Protokol | Açıklama |
|--------|-----------------|----------|----------|
| Email Sunucusu | Outbound | SMTP | Onay bildirimleri |
| CRM | Bidirectional | RFC | Müşteri bilgisi senkron |

---

### BÖLÜM 8: YETKİLENDİRME GEREKSİNİMLERİ

**8.1 Rol Listesi**

| Rol Adı | Açıklama | İzinler |
|---------|----------|---------|
| Z_SD_ONAY_USER | Onay Kullanıcısı | Görüntüleme, Onaylama |
| Z_SD_ONAY_ADMIN | Onay Yöneticisi | Tüm işlemler |
| Z_SD_RAPOR | Raporlama | Sadece görüntüleme |

**8.2 Yetkilendirme Nesneleri**

| Nesne | Alan | Değer | Açıklama |
|-------|------|-------|----------|
| V_VBAK_AAT | AUART | ZSD1 | Sipariş tipi yetkisi |

---

### BÖLÜM 9: RAPORLAMA GEREKSİNİMLERİ

Her rapor için:

| # | Rapor Adı | Açıklama | Seçim Kriterleri | Çıktı Formatı |
|---|-----------|----------|-----------------|---------------|
| RPT-001 | Onay Bekleyen Siparişler | Onay bekleyen tüm siparişler | Tarih aralığı, Müşteri | ALV Grid |
| RPT-002 | Onay Geçmişi | Onaylanan/reddedilen siparişler | Tarih, Onaylayan | ALV + Excel |

---

### BÖLÜM 10: HATA YÖNETİMİ

**10.1 Hata Senaryoları**

| Hata Kodu | Durum | Mesaj | Kullanıcı Aksiyonu |
|-----------|-------|-------|-------------------|
| ERR-001 | Yetkisiz erişim | "Bu işlem için yetkiniz yok" | Sistem yöneticisine başvurun |
| ERR-002 | Geçersiz sipariş | "Sipariş bulunamadı: &1" | Sipariş numarasını kontrol edin |
| ERR-003 | Onay süresi geçmiş | "Onay süresi dolmuştur" | Yeni onay talebi oluşturun |

---

### BÖLÜM 11: TEST GEREKSİNİMLERİ

**11.1 Test Senaryoları**

| Test No | Test Adı | Ön Koşul | Adımlar | Beklenen Sonuç |
|---------|----------|----------|---------|----------------|
| TC-001 | Normal onay | Onay yetkisi olan kullanıcı | 1. ZSD_ONAY aç, 2. Sipariş seç, 3. Onayla | Sipariş onaylandı statüsüne geçer |
| TC-002 | Yetkisiz erişim | Yetkisi olmayan kullanıcı | 1. ZSD_ONAY aç | ERR-001 mesajı görünür |

---

### BÖLÜM 11-A: DANIŞMAN ÖNERİLERİ (onay bekliyor) *(İLKE-2 — sabit bölüm)*

> Kullanıcının **istemediği** ama danışmanın işi iyileştirmek için önerdiği her şey **burada**
> toplanır — gereksinim listesine (§4) sessizce **gömülmez**. Kullanıcı tek yerden görüp
> onaylar/reddeder. **Onaylanan** madde ilgili gereksinime (FR/KR) taşınır ve burada "✓ taşındı"
> işaretlenir. Bu bölüm **boşalmadan** (her öneri karara bağlanmadan) FS mutabakata gitmez.

| # | Öneri `[ÖNERİ]` | Neden (fayda) | Etki/maliyet | Karar (Onay/Ret) |
|---|---|---|---|---|
| Ö-01 | (ekranda şu kolaylık…) | (kullanıcı şunu kazanır) | (ek efor / risk) | ☐ Onay ☐ Ret |

### BÖLÜM 11-B: AÇIK KARARLAR / SORU SETİ *(mutabakat öncesi — build'e ERTELENEMEZ)*

> Danışmanın **karar veremediği** ve **kullanıcının yazdığını netleştiren** her nokta burada
> *seçenekler + önerilen seçenek* ile durur. Sorular **kullanıcının isteği yönünde** derinleşir
> (İLKE-1) — onu değiştirmeye değil, tamamlamaya hizmet eder. **Hiçbir fonksiyonel açık nokta
> "build'de netleşir"e atılamaz.** Tümü kapanınca FS onaylanır.

| # | Açık nokta (hangi isteği netleştiriyor) | Seçenekler | Öneri | Karar |
|---|---|---|---|---|
| S-01 | (ör. "mevcut sipariş eşleşmesi": aynı PO ile 2 açık sipariş olursa?) | a) hata b) en yeni c) açık olan | (b) | — |

---

### BÖLÜM 12: ONAY

| Rol | Ad Soyad | İmza | Tarih |
|-----|----------|------|-------|
| Hazırlayan (Danışman) | | | |
| Gözden Geçiren (Teknik Lider) | | | |
| Onaylayan (Key User) | | | |
| Onaylayan (Proje Müdürü) | | | |

---

## 2.3 FS Yazım Kuralları ve İpuçları

### YAPILMASI GEREKENLER:
- Her gereksinim **test edilebilir** şekilde yazılmalı
- İş kuralları **açık ve net** ifade edilmeli (belirsizlik olmmalı)
- Mockup'lar mutlaka eklenmeli
- Kapsam dışı konular açıkça belirtilmeli
- Müşteri onayı alınmadan geliştirme başlatılmamalı
- Türkçe projede Türkçe yazılmalı (teknik terimler İngilizce kalabilir)

### YAPILMAMASI GEREKENLER:
- Teknik detaylara (kod, tablo adı, fonksiyon adı) yer verilmemeli
- Belirsiz ifadeler kullanılmamalı ("yaklaşık", "genellikle", "bazen" gibi)
- Varsayımlar belirtilmeden yazılmamalı
- Scope creep (kapsam kayması) olmamalı - her değişiklik ayrı FS ile ele alınmalı

---

# BÖLÜM 3: TEKNİK SPESİFİKASYON (TS) DOKÜMANI

## 3.0 TS YAZIM ZİHNİYETİ — "Developer Gözü" + FS Otoritesi + "Ertelenebilir mi?" (ÖNCE OKU)

> **TS'i, bu TS'le *SEN build edeceksin* gibi yaz.** Satır-1'i yazmadan önce bir developer'ın
> soracağı **her soruyu şimdi cevapla.** Bölüm yapısını (3.2) doldurmak yetmez — developer
> tahmine düşerse yanlış/uzun/gitgelli build olur.

**İki değişmez ilke (ihlal = eksik TS):**

**İLKE-3 — FS = KAYNAK OTORİTE.** TS'in **birincil görevi FS'teki HER maddeye (FR/KR) teknik
çözüm üretmektir.** Hiçbir FS gereksinimi TS'te **çözümsüz/atlanmış** kalamaz — izlenebilirlik
matrisi (§5.1) her FR/KR'yi bir TS nesne/metoduna bağlamalıdır (boş satır = eksik TS). TS
yazarken iyileştirme/düşünülmemiş nokta çıkabilir; **meşrudur ama:** (a) FS gereksinimleri
**tam karşılandıktan sonra**, onların üstüne eklenir — FS'i **baypas etmez**; (b) FS'i
değiştiren bir iyileştirme ise TS'e keyfî gömülmez → **FS'e öneri olarak geri beslenir**
(§11-A), onay alınır, sonra TS'e girer.

**İLKE-4 — TS, FS'İ DENETLER (kör itaat DEĞİL).** İLKE-3 "her FR/KR'ye çözüm üret" der; ama TS
yazarken FS **aynı zamanda eleştirel yorumlanır.** Bir FS isteği: **fizibil olmayabilir**;
istendiği gibi yapılınca **hataya** yol açabilir; uygulamanın **başka yerini bozabilir**
(blast-radius — [[feedback_fix-oncesi-where-used-blast-radius]]); **alternatif** bir yolla
yapılması gerekiyor olabilir; ya da düpedüz **yanlış** olabilir. **TS'in en önemli görevlerinden
biri FS'in kalitesini ve doğruluğunu denetlemektir.** Bu değerlendirme TS'ten **önce/sırasında**
yapılır ve bulgular **"BÖLÜM 2-A: FS DENETİMİ"**ne yazılıp kullanıcıya **bilgilendirme** olarak
getirilir — sorunlu bir isteği körü körüne build etmek YASAK: **DUR → denetim bulgusu →
alternatif öner → onay → sonra çözüm.** (TAHMİN YASAK / kanıtlı hareket — çekirdek davranış.)

**İLKE-5 — "ERTELENEBİLİR Mİ?" AYRIMI (kritik).** "Build'de netleşir" cümlesi iki **çok farklı**
şeyi gizler. TS'te bunları **karıştırma:**

| ✅ MEŞRU build-time teyit (ertelenebilir) | ⛔ FONKSİYONEL karar (TS'te KAPANMALI) |
|---|---|
| Tasarımı **değiştirmez**, canlıda **doğrulanır** | Yanlışsa **tasarım/sonuç yanlış** olur |
| DTEL/append adı (ADR 0005 — AI önermez zaten) | Eşleştirme mantığı + **çoklu-eşleşme çözümü** |
| `CONVERT KEY` pre-key alan adı (sürüme bağlı) | Anahtar çözümü **TÜM key alanlarıyla** (ör. KNMT'de vkorg/vtweg) |
| Kütüphane alt-metod syntax'i (`xco_*`) | Veri dönüşümü: tarih / ondalık / **ALPHA / padding** |
| Aktivasyon davranışı (HTTP 200 sahte-OK) | **Birim/UoM** dönüşümü ve karşılaştırma |
| Mesaj no'sunun kesin metni | Hangi **entity/child** hangi alanı taşır (EML/RAP/schedule-line) |
| | **Kenar durumlar:** boş / mükerrer / max / sıfır |
| | Kilit / eşzamanlılık, hata-**birleştirme** kuralı |

> **Sonuç:** TS'in **"BÖLÜM 11-A: BUILD-TIME DOĞRULANACAKLAR"** bölümü YALNIZ sol sütun
> (teknik-teyit) maddelerini içerebilir. Sağ sütun (fonksiyonel karar) oraya **konamaz** —
> o, TS gövdesinde **çözülür** ya da (FS'i etkiliyorsa) FS §11-B'ye geri gider.

**Developer geri-soru simülasyonu — TS'i bitirmeden yap:**
> "Bu TS elime geçti, kodu yazacağım. Satır-1'den önce **neyi bilmem gerekir?**" — çıkan her
> soru TS'te **cevaplı** mı, yoksa 11-A'ya (yalnız meşruysa) mı taşındı? Tipik sorular:
> mevcut kaydı **hangi WHERE** ile bulacağım · **iki eşleşme** olursa hangisi · şu alan **hangi
> tabloda/child'da** · Excel/dış-veri **hangi formatta** gelir, nasıl çeviririm (ALPHA/tarih/
> ondalık) · **birim** farkında karşılaştırma · **boş/mükerrer/max** girdide ne olur · kilit.

## 3.1 TS Nedir?

Teknik Spesifikasyon, FS'te tanımlanan fonksiyonel gereksinimlerin SAP sisteminde **nasıl teknik olarak implemente edileceğini** tanımlayan belgedir. Developer'lar bu belgeyi okuyarak kodu yazabilmelidir. FS olmadan TS yazılmaz.

## 3.2 TS Döküman Yapısı (Zorunlu Bölümler)

### KAPAK SAYFASI

```
Döküman Başlığı     : [Geliştirmenin teknik adı - örn. "ZSD_ONAY - Satış Sipariş Onay Programı"]
Döküman Numarası    : [TS-SD-001]
İlgili FS No        : [FS-SD-001]  ← FS referansı zorunlu
Proje Adı           : [Proje adı]
SAP Sistemi         : [ERP / S/4HANA - versiyon]
Geliştirme Tipi     : [Report / Enhancement / Interface / Form / Workflow / vb.]
Hazırlayan          : [Developer / Teknik Danışman adı]
Tarih               : [GG.AA.YYYY]
Versiyon            : [1.0]
Transport No        : [DEVK9xxxxx]  (varsa)
```

---

### BÖLÜM 1: DÖKÜMAN KONTROLÜ

FS ile aynı yapıda - versiyon geçmişi, dağıtım listesi, ilgili dökümanlar.

**Önemli:** İlgili Dökümanlar bölümünde FS referansı mutlaka yer almalı.

---

### BÖLÜM 2: TEKNİK GENEL BAKIŞ

**2.1 Geliştirme Tipi ve Yaklaşımı**

```
Geliştirme Tipi    : ABAP Report (ALV) / Dialog Program / Class / BAdI / Enhancement
SAP Modülü         : SD / MM / FI / PP / vb.
Etkilenen Süreç    : Satış Sipariş Yönetimi
Geliştirme Metodu  : Yeni geliştirme / Mevcut geliştirme üzerine ekleme
Clean Core Uyum    : Evet / Hayır (S/4HANA için belirtilmeli)
```

**2.2 Teknik Mimari**

Geliştirmenin sistemdeki yerini ve bağlantılarını gösterir:

```
[Kullanıcı] → [ZSD_ONAY Transaction] → [ZCL_SD_ONAY_HANDLER Class]
                                              ↓
                                    [ZVSD_ONAY_H Tablo] + [VBAK/VBAP]
                                              ↓
                                    [Email Gönderimi - SO_NEW_DOCUMENT_ATT_SEND_API1]
```

---

### BÖLÜM 2-A: FS DENETİMİ (fizibilite · yan-etki · alternatif · hata) *(İLKE-4 — sabit bölüm)*

> TS, FS'i yalnız uygulamaz; **denetler.** Her FS gereksinimi (FR/KR) teknik gözle
> değerlendirilir; sorunlular **build'den ÖNCE** kullanıcıya bilgilendirme olarak getirilir.
> Sorun yoksa "✓ istendiği gibi uygulanabilir" satırı yeterlidir (bu bölüm boş bırakılmaz —
> "denetlendi, temiz" de bir sonuçtur).

| FS Md. | Denetim sonucu | Bulgu / gerekçe | Aksiyon |
|---|---|---|---|
| (FR/KR-nn) | ✅ uygulanabilir / ⚠ alternatif gerek / ⛔ fizibil değil / 💥 başka yeri bozar / ✗ FS hatalı | (kanıt: where-used / blast-radius / kural) | (aynen uygula / **alternatif öner→onay** / FS'e geri besle) |

> ⛔ **Sorunlu bir FS maddesi körü körüne build EDİLMEZ** — DUR → bulgu → alternatif → onay →
> sonra çözüm. FS'i değiştiren her düzeltme FS §11-A/§11-B'ye geri döner (İLKE-3).

---

### BÖLÜM 3: GELİŞTİRME NESNELERİ LİSTESİ

**Tüm SAP nesneleri burada listelenir:**

| Nesne Tipi | Nesne Adı | Package | Açıklama | Durum |
|-----------|-----------|---------|----------|-------|
| Program | ZSD_ONAY | ZSD001 | Ana onay programı | Yeni |
| Transaction | ZSD_ONAY | ZSD001 | Transaction kodu | Yeni |
| Class | ZCL_SD_ONAY_HANDLER | ZSD001 | İş mantığı sınıfı | Yeni |
| Table | ZVSD_ONAY_H | ZSD001 | Onay başlık tablosu | Yeni |
| Table | ZVSD_ONAY_P | ZSD001 | Onay pozisyon tablosu | Yeni |
| Data Element | ZVSD_ONAY_STATUS | ZSD001 | Onay durum data elementi | Yeni |
| Domain | ZD_ONAY_STATUS | ZSD001 | Onay durum domain'i | Yeni |
| Message Class | ZSD_ONAY_MSG | ZSD001 | Mesaj sınıfı | Yeni |
| Search Help | ZSH_SD_SIPARIS | ZSD001 | Sipariş arama yardımı | Yeni |

**Naming Convention Kuralları (proje standartlarına göre belirlenir):**
- Program: Z + Modül Kodu + _ + Açıklayıcı İsim
- Class: ZCL_ + Modül + _ + Açıklayıcı İsim
- Table: Z + V/A (Şeffaf/Havuz) + Modül + _ + İsim
- Function Group: Z + Modül + _ + İsim

---

### BÖLÜM 4: VERİ SÖZLÜĞÜ (DATA DICTIONARY) TASARIMI

**4.1 Domain Tanımları**

| Domain Adı | Veri Tipi | Uzunluk | Fixed Values | Açıklama |
|-----------|----------|---------|-------------|----------|
| ZD_ONAY_STATUS | CHAR | 1 | B=Beklemede, O=Onaylandı, R=Reddedildi | Onay durumu |

**4.2 Data Element Tanımları**

| Data Element | Domain | Kısa Metin | Orta Metin | Uzun Metin |
|-------------|--------|-----------|-----------|-----------|
| ZVSD_ONAY_STATUS | ZD_ONAY_STATUS | Durumu | Onay Durumu | Sipariş Onay Durumu |

**4.3 Tablo Tasarımı**

**Tablo: ZVSD_ONAY_H (Onay Başlık Tablosu)**

| Alan Adı | Data Element | Key | Açıklama |
|----------|-------------|-----|----------|
| MANDT | MANDT | X | Mandant |
| ONAY_ID | ZVSD_ONAY_ID | X | Onay ID (UUID) |
| VBELN | VBELN_VA | | Satış Sipariş No |
| STATUS | ZVSD_ONAY_STATUS | | Onay Durumu |
| SEVIYE | ZVSD_ONAY_SEV | | Onay Seviyesi (1/2) |
| ONAYLAYAN | SYUNAME | | Onaylayan Kullanıcı |
| ONAY_TARIHI | SYDATUM | | Onay Tarihi |
| ONAY_SAATI | SYUZEIT | | Onay Saati |
| ACIKLAMA | TEXT255 | | Onay/Red Açıklaması |
| TALEP_EDEN | SYUNAME | | Talebi Oluşturan |
| TALEP_TARIHI | SYDATUM | | Talep Tarihi |
| ERDAT | SYDATUM | | Kayıt Tarihi |
| ERNAM | SYUNAME | | Kaydeden |
| AEDAT | SYDATUM | | Değişiklik Tarihi |
| AENAM | SYUNAME | | Değiştiren |

**Tablo Teknik Özellikleri:**
- Tablo Kategorisi: Transparent Table
- Teslim Sınıfı: A (Uygulama tablosu)
- Veri Tabanı Görünümü: Display/Maintenance allowed

**4.4 Index Tanımları**

| Index Adı | Tablo | Alanlar | Açıklama |
|----------|-------|---------|----------|
| ZVSD_ONAY_H~001 | ZVSD_ONAY_H | VBELN, STATUS | Sipariş numarasına göre hızlı sorgu |

---

### BÖLÜM 4.5: DETAYLI EKRAN / UI TASARIMI

> **Amaç:** Developer'ın ekranı **tahmin etmeden** kurabilmesi için her ekranın görsel ve davranışsal detayını verir. FS'teki mockup üst-seviyedir; TS'teki bu bölüm **field/buton/tablo-kolon + girilen-veriye-göre-etkileşim + hangi servis çağrılır** seviyesinde nettir. Klasik (Dynpro/ALV) ve modern (Fiori/UI5 freestyle + OData) için aynı tablolar doldurulur.
>
> ⛔ **HAM EKRAN GÖRÜNTÜSÜ YAPIŞTIRMA:** Geliştirme tamamlanmış olsa bile gerçek ekranın **resmini olduğu gibi koymak dokümantasyon DEĞİLDİR** — ham görsel; enable/disable koşulunu, validasyonu, çağrılan API/BAPI'yi, alan-davranış etkileşimini **gösteremez**. Tasarım **yapısal tablolarla** (aşağıdaki alan/buton/grid/etkileşim) TANIMLANIR. Görsel eklenecekse **işaretli/açıklamalı** (numara/ok/callout) olmalı ve tabloların yerini TUTMAZ, onları tamamlar.

**4.5.1 Ekran / View Listesi**

| Ekran/View | Tip | Açılış | Amaç |
|---|---|---|---|
| SCR-01 Liste | Fiori UI5 (sap.ui.table grid) / Dynpro ALV | Tile/Tx | Kayıt listeleme, arama, yeni/değiştir nav |
| SCR-02 Yarat | Fiori UI5 freestyle view | Liste→Yeni | Başlık + kalem girişi |
| SCR-03 Değiştir | Fiori UI5 freestyle view | Liste→Değiştir | Mevcut kaydı düzenleme |

**4.5.2 Ekran Yerleşimi (her ekran için ayrı doldurulur)**

Detaylı mockup (FS'tekinden daha net — gerçek etiketler, bölümler, butonlar) +:

> **★ KOLON TAMLIĞI (MUST — eksikse TS eksiktir):** Ekrandaki HER grid/tablonun **TÜM kolonları ve
> her kolonun BAŞLIK etiketi (kolon tanımı)** TS'te açıkça listelenir + netleştirilir — DDIC/varsayılan
> etikete BIRAKILMAZ. *Gerekçe:* structure-merge'de başlık alanın **DTEL'inden** gelir → jenerik veya
> rol-yanlış DTEL AYNI/anlamsız başlık üretir (ör. farklı partner rolleri — sipariş-veren, sevk-adresi,
> ek-muhatap — hepsi `KUNNR` ile "Müşteri" görünür). **Yöntem:** (1) semantik-doğru **standart DTEL**
> kullan (rol-özel: sipariş-veren `KUNAG`/`NAME_AG`, malı-teslim-alan `KUNWE`/`NAME_WE` → ayrı, doğru
> başlık + F1); (2) standart DTEL yoksa (müşteri-özel Z partner fn. vb.) **başlık metnini TS'te AÇIKÇA
> yaz** + `set_coltext` ile ver (ya da kullanıcı-adlı Z DTEL — ADR 0005-D). §4.5.2-(d) açıklama kolonları
> ve (e) fcat-yaklaşımı bu kuralın parçasıdır. Kolonu/etiketi eksik bırakılmış TS = **eksik TS**.

**(a) Alan tablosu**

| Alan (teknik) | Ekran Etiketi | Tip/Uzunluk | Zorunlu | Default | F4 / Value-Help | Düzenlenebilir? | Açıklama/Validasyon |
|---|---|---|---|---|---|---|---|
| soldToParty | Müşteri | char10 | Evet | — | ZSD000_I_CUSTOMER_VH | Yarat'ta E, Değiştir'de H | Boşsa fiyat/sipariş yok |
| priceCode | Fiyat Kodu | char10 | Evet | — | Sağ bakiye tablosundan seç | Seçim | Fiyatlar buradan hesaplanır |
| quantity | Miktar (ADT) | dec | Evet | — | — | E | **PAK katı olmalı** → değilse valueState=Error |

**(b) Buton / Aksiyon tablosu**

| Buton | Etiket | Aksiyon (event) | Enable Koşulu | Çağırdığı Servis (API/BAPI/OData fn) |
|---|---|---|---|---|
| BTN-ADD | Kalem Ekle | onAddItem | Başlık zorunluları dolu | — (local) |
| BTN-SIM | Fiyat Hesapla | onCalculatePrice | Kalem var | OData fn `SimulatePricing` → `API_SALES_ORDER_SIMULATION_SRV` |
| BTN-SAVE | Kaydet | onSaveOrder | priceCalculated + hata yok | OData action `CreateSalesOrder`/`UpdateSalesOrder` → EML `I_SalesOrderTP` (façade) |

**(c) Tablo / Grid tasarımı** (liste/kalem tablosu varsa)

| Kolon | Etiket | Tip | Düzenlenebilir? | Sort/Filter | Hesaplama/Format |
|---|---|---|---|---|---|
| material | Malzeme | char | E (Yarat) | Evet | F4 |
| quantity | Miktar (ADT) | dec | E | Evet | PAK katı kontrol |
| packageQty | Miktar (PAK) | dec | H | Hayır | = miktar × PakFactor |
| netAmount | Tutar | curr | H | Evet | Fiyat Hesapla doldurur |

**(d) Açıklama / tanım kolonları kararı (ZORUNLU — atlanamaz)**

> Ekranda veya grid'de **kod alanı** olarak listelenen HER alan için (müşteri no, ship-to/WE,
> ilave partner/ZW, sipariş tipi/AUART, malzeme, birim, plant, depo, ödeme/teslim koşulu vb.),
> o kodun **açıklama/tanım metninin** tabloya **ayrı kolon olarak eklenip eklenmeyeceği TS
> hazırlanırken KARARA BAĞLANIR ve bu bölümde AÇIKÇA belirtilir.** Kullanıcının salt koddan
> tanıyamayacağı bir kod-kolonu **tanımsız bırakılamaz**: ya açıklama kolonu eklenir — **kaynak
> tablo/alan + dil** yazılır (ör. müşteri→`KNA1-NAME1`, sipariş tipi→`TVAKT-BEZEI` SPRAS=oturum,
> malzeme→`MAKT-MAKTX`) — ya da "açıklama gerekmez" **gerekçesiyle bilinçli olarak dışlanır.**
> Bu karar boş bırakılırsa build'de eksik/tanımsız kolon riski doğar (kod görünür, anlamı görünmez).

| Kod alanı | Açıklama eklensin mi? | Kaynak (tablo-alan · dil) | Karar/gerekçe |
|---|---|---|---|
| (ör. kunwe/WE) | ✅ Evet | KNA1-NAME1 | Kullanıcı adı görmeli |
| (ör. auart) | ✅ Evet | TVAKT-BEZEI · oturum dili | Tip kodu tek başına yetersiz |
| (ör. mandt) | ⛔ Hayır | — | Teknik alan, anlam gerekmez |

**(e) Field catalog yaklaşımı — DDIC-structure mi, manuel mi? (klasik ALV — ZORUNLU KARAR)**

> Klasik ALV (`CL_GUI_ALV_GRID` / SALV) içeren ekranda field catalog'un **DDIC output-structure'dan
> merge** mi (`Z…_S_…` + `i_structure_name`/`LVC_FIELDCATALOG_MERGE`) yoksa **manuel `lvc_t_fcat`** mi
> kurulacağı TS'te **KARARA BAĞLANIR ve gerekçesiyle yazılır** — developer sessizce seçmez (ADR 0012
> rafinasyonu). **Structure tercih:** miktar+birim ondalık · para+PB · çok kolon · kod→tanım (açıklama)
> kolonları · tekrar-kullanım (DDIC tipleri + QUAN-birim-ref + CURR-ref **otomatik** gelir → manuel hata
> kapanır). **Manuel meşru:** basit / az-kolon / ad-hoc rapor. Structure seçildiyse: **structure adı +
> alan→DTEL eşlemesi** BÖLÜM 4 (DDIC) altında verilir; §4.5.2-(d) açıklama kolonları da structure alanı olur.
>
> **DTEL SEMANTİĞİ = KOLON BAŞLIĞI (kritik):** structure-merge'de kolon başlığı alanın **DTEL'inden**
> gelir. **Semantik-doğru standart DTEL seç** — aynı jenerik DTEL'i (ör. `KUNNR`) farklı roller için
> kullanmak AYNI/yanıltıcı başlık üretir (ör. sipariş-veren + sevk-adresi + ek-muhatap hepsi "Müşteri").
> Rol-özel standart DTEL VARSA kullan (ör. sipariş-veren `KUNAG`/`NAME_AG`, malı-teslim-alan
> `KUNWE`/`NAME_WE` → ayrı, doğru başlık + F1). **Standart DTEL YOKSA** (ör. müşteri-özel Z partner
> fonksiyonu): iki yol — (a) **Z DTEL** (kullanıcı adlandırır — ADR 0005-D, AI önermez) VEYA (b)
> **`set_coltext` ile kod-etiketi**. Hangisi olursa olsun **o kolonun başlık metni TS'te AÇIKÇA
> NETLEŞTİRİLİR** (jenerik DTEL etiketine — "Müşteri"/"Ad" — güvenilmez; alanın gerçek iş-anlamı yazılır).

| ALV grid | Yaklaşım | Gerekçe |
|---|---|---|
| (ör. kalem grid — miktar/birim/tanım) | DDIC-structure merge | ondalık+tanım DDIC'ten; manuel hata riski |
| (ör. basit 3-kolon log) | Manuel lvc_t_fcat | tipsiz/az kolon; structure gereksiz |

**4.5.3 Etkileşim Matrisi (girilen veriye göre davranış)**

| Tetikleyici (event) | Koşul | Sonuç/Davranış | Çağrılan Servis |
|---|---|---|---|
| Malzeme seçildi | — | Ad/birim/PAK/stok otomatik dolar | OData read `ZSD001_C_MAT_LOOKUP` |
| Miktar değişti | PAK katı değil | Satır kırmızı (valueState=Error), Kaydet bloke | — |
| Fiyat kodu değişti (Değiştir) | mevcut≠yeni | Onay sor → fiyat geçersizleşir | — |
| Kaydet | hatalı kalem var | Bloke + mesaj listesi | — |

**4.5.4 Kullanılan API / BAPI / OData Servisleri ve Test**

| İşlev | Servis | Tip | Test Yöntemi |
|---|---|---|---|
| Fiyat simülasyonu | API_SALES_ORDER_SIMULATION_SRV | Released OData | SE37/Postman + **test variant** (örnek payload) |
| Sipariş oluştur/değiştir | I_SalesOrderTP (EML) / BAPI_SALESORDER_CREATEFROMDAT2 | Released BO / BAPI | SE37 **test variant** (kayıtlı girdi seti) |

> **Not (RAP/Fiori projeler):** Ekran = UI5 freestyle view; "transaction" yerine **OData servis + function/action import** belirtilir. Klasik Dynpro projede aynı tablolar Dynpro field/PF-status/event'lerine map edilir.

---

### BÖLÜM 5: PROGRAM / SINIF TASARIMI

**5.1 Program Yapısı**

```
ZSD_ONAY (Report/Dialog Program)
├── Seçim Ekranı (SELECTION-SCREEN)
│   ├── Sipariş No aralığı
│   ├── Tarih aralığı
│   └── Durum filtresi
├── Ana Mantık (START-OF-SELECTION)
│   ├── Veri okuma (ZCL_SD_ONAY_HANDLER=>get_pending_list)
│   └── ALV gösterimi (ZCL_SD_ONAY_HANDLER=>display_alv)
└── Kullanıcı Aksiyonları
    ├── Onayla (ZCL_SD_ONAY_HANDLER=>approve)
    ├── Reddet (ZCL_SD_ONAY_HANDLER=>reject)
    └── Detay (ZCL_SD_ONAY_HANDLER=>show_detail)
```

**5.2 Class Tasarımı**

**Class: ZCL_SD_ONAY_HANDLER**

| Method Adı | Tipi | Girdi | Çıktı | Açıklama |
|-----------|------|-------|-------|----------|
| GET_PENDING_LIST | Static | IV_DATUM_FROM, IV_DATUM_TO | ET_LIST | Onay bekleyen siparişleri getirir |
| APPROVE | Instance | IV_ONAY_ID, IV_ACIKLAMA | EV_SUCCESS, EV_MSG | Siparişi onaylar |
| REJECT | Instance | IV_ONAY_ID, IV_ACIKLAMA | EV_SUCCESS, EV_MSG | Siparişi reddeder |
| SEND_NOTIFICATION | Private | IV_VBELN, IV_STATUS | | Email bildirimi gönderir |
| CHECK_AUTHORITY | Private | IV_ONAY_ID | EV_AUTHORIZED | Yetki kontrolü |

**5.3 Algoritma / İş Mantığı Pseudocode**

```
METHOD approve:
  1. Giriş parametrelerini validate et
  2. ONAY_ID için ZVSD_ONAY_H'dan kaydı oku
  3. CHECK_AUTHORITY çağır
     - Yetki yoksa: EV_SUCCESS = False, EV_MSG = 'E001', RETURN
  4. STATUS = 'B' (Beklemede) değil ise hata döndür
  5. Onay seviyesini kontrol et (SEVIYE)
     - Seviye 1 ise: STATUS = 'O1' (1. Onay Tamamlandı)
       - Tutar > 50.000 TL ise: 2. seviye onay talebi oluştur
       - Tutar <= 50.000 TL ise: STATUS = 'O' (Onaylandı), SAP siparişini serbest bırak
     - Seviye 2 ise: STATUS = 'O' (Onaylandı), SAP siparişini serbest bırak
  6. ZVSD_ONAY_H güncelle (MODIFY)
  7. SEND_NOTIFICATION çağır (onaylayan ve talep eden'e email)
  8. COMMIT WORK
  9. EV_SUCCESS = True
ENDMETHOD.
```

---

### BÖLÜM 6: VERİTABANI ERİŞİM TASARIMI

**6.1 Kullanılan SAP Standart Tabloları**

| Tablo | Açıklama | Kullanım Amacı | Erişim Tipi |
|-------|----------|----------------|-------------|
| VBAK | Satış Sipariş Başlık | Sipariş bilgileri okuma | SELECT |
| VBAP | Satış Sipariş Pozisyon | Pozisyon bilgileri okuma | SELECT |
| KNA1 | Müşteri | Müşteri adı | SELECT |
| USR02 | Kullanıcı | Kullanıcı email bilgisi | SELECT |

**NOT: SAP Standart tablolarına INSERT/UPDATE/DELETE yapılmaz. Bunun yerine standart BAPI/FM kullanılır.**

**6.2 Kritik SELECT'ler**

```abap
" Onay bekleyen sipariş listesi
SELECT a~onay_id, a~vbeln, a~status, a~talep_tarihi,
       b~kunnr, b~netwr, b~waerk
  FROM zvsd_onay_h AS a
  INNER JOIN vbak   AS b ON b~vbeln = a~vbeln
  WHERE a~mandt  = @sy-mandt
    AND a~status = 'B'
    AND a~talep_tarihi BETWEEN @lv_datum_from AND @lv_datum_to
  INTO TABLE @DATA(lt_onay_list).
```

**6.3 Performans Kuralları**

- SELECT * kullanılmaz, sadece ihtiyaç duyulan alanlar seçilir
- WHERE koşulsuz SELECT kullanılmaz
- Loop içinde SELECT yapılmaz (for all entries veya JOIN kullanılır)
- Büyük veri setlerinde PACKAGE SIZE kullanılır

---

### BÖLÜM 7: ENHANCEMENTler VE BADİ'ler

**7.1 Kullanılan Enhancement / BAdI / User Exit**

| # | Enhancement Tipi | Enhancement Adı | İmplantasyon Adı | Açıklama |
|---|----------------|-----------------|-----------------|----------|
| 1 | BAdI | SD_SALES_ORDER_SAVE | ZSD_ONAY_SAVE_IMPL | Sipariş kaydetmede onay talebi oluştur |
| 2 | Enhancement Spot | ES_SD_VBAK_CHECK | ZSD_VBAK_CHECK_ENH | Sipariş validasyon sonrası kontrol |

**7.2 BAdI Implementasyon Detayı**

```
BAdI: SD_SALES_ORDER_SAVE
Metod: CHANGE_AT_SAVE
Amaç: Sipariş kaydedildiğinde belirli koşullarda onay talebi oluşturmak

Pseudocode:
  IF ls_vbak-netwr > 10000 AND ls_vbak-gbstk = 'A'  " Açık sipariş
    IF NOT onay_mevcut( ls_vbak-vbeln )              " Onay zaten yoksa
      ZCL_SD_ONAY_HANDLER=>create_approval_request(
        iv_vbeln = ls_vbak-vbeln
        iv_seviye = 1
      ).
    ENDIF.
  ENDIF.
```

---

### BÖLÜM 8: FORM / ÇIKTI TASARIMI (varsa)

**8.1 Form Bilgileri**

| Özellik | Değer |
|---------|-------|
| Form Tipi | Adobe Form / Smartform / SAPscript |
| Form Adı | ZSD_ONAY_FORM |
| Çağıran Program | ZSD_ONAY_PRINT |
| Çıktı Tipi | LP01 |
| Kağıt Boyutu | A4 |

**8.2 Form Yapısı**

- Header bölümü: Şirket logosu, başlık, tarih
- Detay bölümü: Sipariş bilgileri, pozisyonlar
- Footer bölümü: İmza alanları

---

### BÖLÜM 9: INTERFACE / RFC TASARIMI (varsa)

**9.1 RFC Fonksiyon Modülü**

```
Fonksiyon Modülü: Z_SD_ONAY_RFC_GET_LIST
Grup: ZSD_ONAY_RFC
Amaç: Dış sistemlerin onay listesine erişimi

Import Parametreler:
  IV_DATUM_FROM   TYPE SYDATUM   " Başlangıç tarihi
  IV_DATUM_TO     TYPE SYDATUM   " Bitiş tarihi

Export Parametreler:
  EV_RETURN_CODE  TYPE SYSUBRC   " 0=Başarı

Tables Parametreler:
  ET_ONAY_LIST    TYPE ZVSD_ONAY_LIST_T  " Onay listesi

Exception:
  NOT_AUTHORIZED  " Yetki hatası
  SYSTEM_ERROR    " Sistem hatası
```

---

### BÖLÜM 10: HATA YÖNETİMİ (TEKNİK)

**10.1 Mesaj Sınıfı Tanımları**

| Mesaj Sınıfı | No | Tip | Metin | Açıklama |
|-------------|-----|-----|-------|----------|
| ZSD_ONAY_MSG | 001 | E | Yetki hatası: & işlemi için yetkiniz yok | Yetki hatası |
| ZSD_ONAY_MSG | 002 | S | Sipariş & başarıyla onaylandı | Başarı mesajı |
| ZSD_ONAY_MSG | 003 | W | Sipariş & zaten onaylanmış durumda | Uyarı |
| ZSD_ONAY_MSG | 004 | A | Sistem hatası: & | Kritik hata |

**10.2 Exception Handling**

```abap
TRY.
    lo_handler->approve(
      EXPORTING iv_onay_id  = lv_onay_id
                iv_aciklama = lv_aciklama
      IMPORTING ev_success  = lv_success
                ev_msg      = lv_msg ).
  CATCH zcx_sd_onay_exception INTO lx_exc.
    " Loglama
    MESSAGE lx_exc->get_text( ) TYPE 'E'.
ENDTRY.
```

---

### BÖLÜM 11: TEST SENARYOLARI (TEKNİK)

**11.1 Unit Test Planı**

| Test No | Test Sınıfı | Test Metodu | Test Koşulu | Beklenen Sonuç |
|---------|------------|------------|-------------|----------------|
| UT-001 | ZCL_SD_ONAY_TEST | TEST_APPROVE_OK | Geçerli onay_id, yetkili kullanıcı | SUCCESS = True |
| UT-002 | ZCL_SD_ONAY_TEST | TEST_APPROVE_NO_AUTH | Yetkisiz kullanıcı | Exception: NOT_AUTHORIZED |
| UT-003 | ZCL_SD_ONAY_TEST | TEST_GET_LIST_EMPTY | Koşula uyan kayıt yok | ET_LIST boş döner |

**11.2 Entegrasyon Test Planı**

| Test No | Açıklama | Test Adımları | Beklenen |
|---------|----------|--------------|----------|
| IT-001 | Uçtan uca onay akışı | Sipariş gir → onay talebi oluşsun → onayla → sipariş statüsü değişsin | Tüm adımlar başarılı |

---

### BÖLÜM 11-A: BUILD-TIME DOĞRULANACAKLAR *(YALNIZ teknik-teyit — İLKE-5)*

> Buraya **yalnız** İLKE-5 sol-sütun maddeleri girer: tasarımı değiştirmeyen, canlıda
> doğrulanacak teknik teyitler (DTEL adı · `CONVERT KEY` pre-key alanı · kütüphane alt-metod
> syntax'i · aktivasyon sahte-OK · kesin mesaj metni). **Fonksiyonel karar buraya KONAMAZ** —
> o TS gövdesinde çözülür ya da FS §11-B'ye gider. Denetim: "bu madde yanlış çıkarsa *tasarım/
> sonuç* değişir mi?" → **evet ise buraya ait değildir.**

| # | Doğrulanacak (teknik) | Yöntem | Neden ertelenebilir (tasarımı değiştirmez) |
|---|---|---|---|
| D-01 | (ör. `CONVERT KEY` pre-key alan adı) | ilk test / `adt_syntax_check` | sürüme bağlı ad; akış aynı |

---

### BÖLÜM 12: TRANSPORT STRATEJİSİ

**12.1 Transport Listesi**

| Transport No | Açıklama | İçerik | Hedef Sistem |
|-------------|----------|--------|-------------|
| DEVK9xxxxx | ZSD_ONAY - DD Objects | Tablolar, Domain, Data Element | QAS → PRD |
| DEVK9xxxxx | ZSD_ONAY - Programs | Programlar, Sınıflar, Function | QAS → PRD |

**12.2 Transport Sırası**

1. Data Dictionary nesneleri (tablo, domain, data element)
2. Message class
3. Program, class, function group
4. Transaction, authorization objects
5. Customizing (varsa)

---

### BÖLÜM 13: ONAY

| Rol | Ad Soyad | İmza | Tarih |
|-----|----------|------|-------|
| Hazırlayan (Developer) | | | |
| Gözden Geçiren (Teknik Lider) | | | |
| Onaylayan (SAP Mimar) | | | |

---

## 3.3 TS Yazım Kuralları ve İpuçları

### YAPILMASI GEREKENLER:
- Her nesne için naming convention belirtilmeli
- Pseudocode algoritma açıklamaları olmalı (gerçek kod değil, mantık açıklaması)
- Performans etkileri düşünülmeli ve belirtilmeli
- SAP standart nesnelere müdahale minimum tutulmalı
- BAdI/Enhancement tercih edilmeli, User Exit son çare olmalı
- Clean Core prensipleri S/4HANA projesinde belirtilmeli
- Transport stratejisi mutlaka yazılmalı

### YAPILMAMASI GEREKENLER:
- FS'e referans verilmeden TS yazılmamalı
- Tüm kodun TS'e yazılmamalı (pseudocode yeterli)
- Standart SAP tablolarına direkt veri manipülasyonu önerilmemeli
- Naming convention dışı nesne adı kullanılmamalı
- Test senaryoları atlanmamalı

---

# BÖLÜM 4: KULLANICI DÖKÜMANI (KD)

## 4.1 KD Nedir?

Kullanıcı Dökümanı, bir geliştirmeyi **hiç bilmeyen son kullanıcıya** "bu nedir, ne işe yarar, nasıl kullanırım" sorularını **adım adım** anlatan başucu kılavuzudur. Kullanıcının yalnızca **kendi günlük kullandığı SAP ekranlarını** bildiği varsayılır; teknik bilgi beklenmez. FS/TS *geliştirme için*, KD *kullanım için*. Bir **beşinci sınıf öğrencisinin** anlayabileceği sadelikte olmalıdır.

> **Altın kural:** Teknik HİÇBİR şey yok (tablo adı, FM, BAPI, kod). Geçen her terim sözlükte sade açıklanır. **Her mesaj/hatanın yanında "ne yapmalısın" aksiyonu** olur. Metnin çoğunluğu **işaretli (annotated) ekran görüntüsü** ile desteklenir (ok / daire / numara sırası) — görselli talimat görev tamamlamayı ~%67 artırır.

## 4.2 KD Döküman Yapısı (Zorunlu Bölümler)

### KAPAK SAYFASI
```
Döküman Başlığı   : [Kullanıcı-dostu ad — örn. "Sipariş Uygulaması — Kullanıcı Kılavuzu"]
Döküman No        : [KD-SD-001]  (KD + modül + sıra)
İlgili FS / TS No : [FS-SD-001 / TS-SD-001]
Uygulama/İşlem    : [Erişim adı — tile/transaction]
Kimler İçin       : [Hedef kullanıcı rolü — örn. "Satış / Sevkiyat kullanıcıları"]
Hazırlayan        : [Danışman / Key User]
Tarih / Versiyon  : [GG.AA.YYYY / 1.0]
Durum             : [Taslak / Onaylandı]
```

### BÖLÜM 1: BU KILAVUZ HAKKINDA *(ilk sayfa — "bana uygun mu?")*
İlk sayfa kullanıcının **bu kılavuzun ona uygun olup olmadığını** anında anlamasını sağlar:
- **Ne anlatır:** 1 cümle ("Bu kılavuz siparişleri SAP'de oluşturmayı/değiştirmeyi anlatır").
- **Kimin için:** hangi rol/iş yapan kişi.
- **Nasıl okunur:** yeni başlayan baştan; deneyimli ilgili bölüme atlar (içindekiler).
- **Takıldığında kim:** destek/Key User iletişimi (1 satır, en başta).
- **Varsayım:** "SAP'de kendi kullandığın ekranları bildiğin varsayılır; teknik bilgi gerekmez."

### BÖLÜM 2: GENEL BAKIŞ — NE / NEDEN / SONUÇ
- **Bu uygulama nedir** (1-2 sade paragraf).
- **Ne işe yarar / hangi işini kolaylaştırır** (amaç + fayda; eskiden nasıldı → şimdi nasıl, kullanıcı gözünden).
- **SONUÇ — arka planda ne oluşur (kritik):** bu işlemi yapınca sistemde ne yaratılır, sade dille. Örn: *"Kaydet'e bastığında SAP'de gerçek bir **satış siparişi** oluşur; daha sonra bundan **teslimat ve fatura** kesilebilir."* Kullanıcı sonucun ne olduğunu görmeli.
- **Üst-seviye akış:** 3-5 maddelik resim ("Müşteri seç → kalem gir → fiyat hesapla → kaydet").

### BÖLÜM 3: BAŞLAMADAN ÖNCE (Ön Koşullar)
- **Erişim/yetki:** hangi rol gerekir; **yoksa ne yaparsın** (kime başvurursun).
- **Elinde ne olmalı:** işlem öncesi gerekli bilgi/ana veri (müşteri no, malzeme listesi, müşteri Excel'i vb.).
- **Nereden açılır:** Fiori Launchpad'de hangi grup/tile (veya transaction/URL); ilk giriş notları (örn. "ilk açılışta kullanıcı/şifre bir kez sorulabilir").

### BÖLÜM 4: EKRAN TANITIMI (Genel Yerleşim)
Ana ekranın **işaretli ekran görüntüsü** + her bölümün ne işe yaradığı (numaralı callout):
```
[EKRAN GÖRÜNTÜSÜ — numaralı oklarla]
① Başlık alanı: müşteri, sipariş türü, fiyat kodu burada seçilir
② Kalem tablosu: sipariş edilen malzemeler ve miktarlar
③ Özet: toplam tutar, KDV, paket/ağırlık
④ Butonlar: Kalem Ekle, Fiyat Hesapla, Kaydet
```

### BÖLÜM 4-A: LİSTE/TABLO EKRANI ÖZELLİKLERİ *(grid başlık araçları — ZORUNLU/FIX)*

> **Kural (ADR 0008 + [[feedback_grid-liste-standardi]] doküman karşılığı):** Uygulamada **standart liste/tablo ekranı** (grid = `sap.ui.table` + TablePersonalizer) varsa, KD'de **mutlaka bu başlık altında** tablonun ortak araçları anlatılır. Bu bölüm her grid-listeli uygulamanın KD'sinde **otomatik/sabit** yer alır — atlanmaz, kısaltılmaz. Her madde **ne işe yarar + nasıl kullanılır** + **işaretli ekran görüntüsü** ile verilir.

İşaretli ekran görüntüsü (liste başlığı + bir kolon başlığı menüsü açık):
```
[LİSTE EKRANI — başlık çubuğu + kolon başlığı menüsü, numaralı oklarla]
```

| Özellik | Nerede | Ne işe yarar | Nasıl kullanılır |
|---|---|---|---|
| **Sıralama** | Kolon başlığına tıkla | Listeyi o kolona göre artan/azalan dizer | Kolon başlığı → "Artan/Azalan Sırala" |
| **Filtreleme** | Kolon başlığına tıkla | O kolonda operatörlü (içerir/eşittir/arasında…) süzme | Kolon başlığı → Filtre → değer gir; filtreli kolon başlığı belirginleşir |
| **Kolonlar (göster/gizle)** | Başlık çubuğu → *Kolonlar* | Hangi kolonların görüneceğini seçer | Butona tıkla → kolon listesinden işaretle/kaldır |
| **Varyant (görünüm)** | Başlık çubuğu → *Varyant* | Kolon/sıra/filtre düzenini kaydeder, sonra tek tıkla geri yükler; varsayılan yapılabilir | "Farklı Kaydet" ile adlandır → sonra listeden seç / "Varsayılan Yap" |
| **Excel'e Aktar** | Başlık çubuğu → *Excel'e Aktar* | Listeyi Excel dosyası olarak indirir | Butona tıkla → kapsam sor (**Görünür kolonlar / Tüm kolonlar**) → dosya iner |
| **Yenile** | Başlık çubuğu → *Yenile* | Listeyi sunucudan güncel veriyle tazeler | Butona tıkla (kayıt eklendi/değişti ise) |
| **Filtre çubuğu** *(varsa)* | Listenin üstünde katlanabilir panel | Arama kriterleri (alanlar + F4) girip *Listele/Ara* | Paneli aç → kriter gir → *Listele*; *Temizle* sıfırlar |

> **Not:** Bu bölüm araçların *varlığını ve nasıl kullanılacağını* anlatır; uygulamaya özel iş akışları **BÖLÜM 5**'te kalır. Uygulama m.Table (mobil) gibi grid-dışı liste kullanıyorsa bu bölüm o ekranın gerçek araçlarına göre uyarlanır (ADR 0008 istisnası).

### BÖLÜM 5: ADIM ADIM İŞ AKIŞLARI *(çekirdek bölüm — "nasıl yaparım")*
Her tipik görev için **numaralı adımlar + ekran görüntüsü**. Emir kipi ("tıkla / gir / seç"):
```
► Yeni sipariş oluşturmak için:
  1. Ana ekranda [Yeni Sipariş] butonuna tıkla.
  2. Başlıkta Müşteri'yi seç (büyüteç → listeden). → Ekran görüntüsü
  3. [Kalem Ekle] ile malzeme ve miktar gir.
  4. [Fiyat Hesapla]'ya tıkla → tutarlar dolar.
  5. [Kaydet] → "Sipariş 100000xx oluşturuldu" mesajını görürsün.
► Mevcut siparişi değiştirmek için: ...
► Excel'den toplu kalem eklemek için: ...
```

### BÖLÜM 6: ALAN GİRİŞ REHBERİ — NE / NASIL / NEDEN ZORUNLU
| Alan (ekran etiketi) | Ne girilir | Format / Örnek | Zorunlu mu? | **Neden / boş bırakırsan** | Otomatik mi? |
|---|---|---|---|---|---|
| Müşteri | Sipariş veren cari | Listeden seç | **Evet** | Müşteri olmadan fiyat/sipariş oluşmaz | Hayır |
| Fiyat Kodu | Sözleşme fiyat kodu | Sağ tablodan seç | **Evet** | Fiyatlar bu koddan hesaplanır | Hayır |
| Miktar | Sipariş adedi | Sayı; **PAK katı** olmalı | Evet | PAK katı değilse satır kırmızı, kaydedemezsin | Hayır |
| Tutar | — | — | Hayır | Sistem hesaplar | **Evet (Fiyat Hesapla)** |

### BÖLÜM 7: BUTONLAR VE OPERASYONLAR *(event tetikleyen HER şey)*
| Buton / Operasyon | Ne yapar | Ne zaman kullanılır | **Arka planda sonuç** |
|---|---|---|---|
| Kalem Ekle | Tabloya boş satır ekler | Malzeme eklerken | — |
| Fiyat Hesapla | Girilen kalemlerin fiyatını çeker, KDV dahil toplamı gösterir | **Kaydetmeden önce** zorunlu | Henüz sipariş oluşmaz (simülasyon) |
| Kaydet | Siparişi oluşturur/günceller | Tüm zorunlular dolduğunda | **SAP'de gerçek sipariş + notlar oluşur** |
| Toplu Ekle | Excel'den yapıştırılan kalemleri tek tek ekler | 100+ kalem girerken | — |

### BÖLÜM 8: YAPILMASI VE YAPILMAMASI GEREKENLER
- ✅ **Yapılması:** Kaydetmeden önce mutlaka **Fiyat Hesapla** çalıştır; miktarı PAK katı gir; fiyat kodunu değiştirince fiyatı yeniden hesapla.
- ⛔ **Yapılmaması:** Aynı siparişi iki kişi aynı anda açıp değiştirmeye çalışma (kilit uyarısı alırsın); tanımsız malzeme kodu elle yazma; tutarı elle değiştirmeye çalışma (sistem hesaplar).

### BÖLÜM 9: HATA VE MESAJLAR — KARŞILAŞINCA NE YAPMALI
Hata mesajı = **kusur değil, yönlendirme**. Kullanıcıyı suçlama; her satırda net **aksiyon** ver. Mesaj metnini **birebir** yaz (kullanıcı arayıp bulabilsin):
| Gördüğün mesaj | Ne demek | Neden olur | **NE YAPMALISIN** |
|---|---|---|---|
| "Kaydetmeden önce lütfen fiyat hesaplayın" | Henüz fiyat hesaplanmadı | Fiyat Hesapla'ya basmadın | [Fiyat Hesapla]'ya tıkla, sonra Kaydet |
| "Miktar PAK katı olmalı (1 PAK = 5 ADT)" | Girdiğin miktar paket katı değil | Örn. 3 girdin, 5'in katı olmalı | Miktarı 5/10/15… yap |
| "Sipariş X tarafından düzenleniyor" | Başkası bu siparişi açmış | Aynı anda iki kişi | Diğeri kapatınca tekrar dene; acilse o kişiye haber ver |
| "Malzeme tanımsız / bu üretim yerinde yok" | Girdiğin kod sistemde yok | Yanlış/eksik kod | Kodu kontrol et; emin değilsen büyüteçle ara |

> **Hâlâ çözülmezse:** Bölüm 12'deki destek kanalına başvur; **mesajın tam metnini + sipariş numarasını** ilet.

### BÖLÜM 10: SIKÇA SORULAN SORULAR (SSS)
Sahadan gelen gerçek sorular + sade cevaplar. Örn: *"Fiyat neden 0 geldi?" → Müşterinin vergi/fiyat ayarını Key User ile kontrol ettir.* / *"Notlar nereye kaydoluyor?" → Siparişin başlık metinlerine; VA03'te de görünür.*

### BÖLÜM 11: TERİMLER SÖZLÜĞÜ
Geçen her terim sade açıklanır (kısaltmalar açılır). Örn: **PAK** = paket; **Sevk Emri** = …; **Fiyat Kodu** = sözleşmeye bağlı fiyat seti; **KDV** = ….

### BÖLÜM 12: DESTEK VE İLETİŞİM — "Hâlâ takıldın mı?"
Takılınca kime/nasıl başvurulur: Key User adı/iletişim, IT destek/ticket kanalı, çalışma saatleri. Her kılavuzun sonunda bu bölüm olmalı.

### BÖLÜM 13: ONAY
| Rol | Ad Soyad | İmza | Tarih |
|-----|----------|------|-------|
| Hazırlayan (Danışman/Key User) | | | |
| Gözden Geçiren (Key User) | | | |
| Onaylayan (Süreç Sahibi) | | | |

---

## 4.3 KD Yazım Kuralları

### YAPILMASI GEREKENLER
- **Sade dil** (5. sınıf seviyesi), kullanıcı için yaz — developer için değil; jargon yok, kısaltmaları aç.
- Çoğunluk **işaretli ekran görüntüsü** (ok/daire/numara); metin duvarı yerine **numaralı adımlar**.
- ⭐ **TÜM SUB-SCREEN'LER GÖSTERİLİR VE ANLATILIR:** Uygulamada açılan **her** alt ekran — dialog/pop-up, popover, value-help (F4) penceresi, picker/seçim penceresi, sihirbaz adımı — KD'de **kendi ekran görüntüsü + ne işe yaradığı + alan/kolon ve buton fonksiyonları** ile yer almalıdır. Bir ekrandan açılan başka bir pencere de bir ekrandır (ör. "Sipariş Ekle" picker'ı, "Yeni Adres" dialog'u). Yalnız ana/routed sayfaları anlatıp modal pencereleri atlamak EKSİK KD'dir. **Yöntem:** önce uygulamanın view + fragment (dialog/popover) envanterini çıkar → her birini KD'de bir bölüme eşle.
- **Emir kipi**: "tıkla, gir, seç" (etken, kısa cümle).
- ⭐ **GRID LİSTESİ VARSA BÖLÜM 4-A ZORUNLU:** Standart liste/tablo ekranı (`sap.ui.table` + TablePersonalizer, ADR 0008) içeren her uygulamada tablo başlık araçları (sıralama/filtreleme/kolonlar/varyant/Excel'e aktar/yenile + varsa filtre çubuğu) **BÖLÜM 4-A başlığı altında** anlatılır — sabit/fix bölüm, atlanmaz.
- İçindekiler + her bölüm net başlıkla; role göre grupla.
- **Her mesaj/hatanın yanında aksiyon** olsun; mesaj metnini **birebir** yaz (aranabilir).
- Görev-bazlı ("X yapmak için: 1…2…"), "How to" odağı; başta bir **Hızlı Başlangıç**.
- Terim sözlüğü + "Hâlâ takıldın mı? → destek" bölümü zorunlu.

### YAPILMAMASI GEREKENLER
- **Teknik detay YOK** (tablo/FM/BAPI/kod/transaction-internals); bunlar TS'tedir.
- Kullanıcıyı suçlama ("yanlış girdin" değil → "şunu yap"); BÜYÜK HARF/ünlem yığma.
- Tek genel mesaj yerine **her duruma ayrı** açıklama+aksiyon.
- Ekran görüntüsüz uzun anlatım; varsayım ("herkes bilir") ile atlama.
- **Mockup/temsili çizim kullanma** — KD'de geliştirme bittiği için **gerçek uygulama ekranının görüntüsü** kullanılır (FS/TS'in aksine). Ama görüntü **işaretli/numaralı** (callout) olmalı; ham/açıklamasız tek başına resim yeterli değildir.

## 4.4 KD Kalite Kontrol Listesi
```
[ ] İlk sayfa: ne/kim/takılınca-kim net (relevance)
[ ] Genel bakış: amaç + ARKA PLAN SONUÇLARI (ne oluşur) yazılı
[ ] Ön koşullar (yetki/ana veri/erişim) belirtilmiş
[ ] Ekran tanıtımı işaretli ekran görüntüsüyle
[ ] TÜM ekran görüntüleri MOCK/TEMİZ örnek veriyle (client-model injection) — kirli/gerçek backend kaydı YOK (§1.3)
[ ] Grid-liste varsa BÖLÜM 4-A (tablo araçları: sıralama/filtre/kolonlar/varyant/Excel/yenile) var (§4-A)
[ ] TÜM sub-screen'ler (dialog/popover/value-help/picker/sihirbaz) ayrı bölüm + görüntü + fonksiyon ile var
    → uygulamanın view + fragment envanteri çıkarıldı, her biri KD'de eşlendi (atlanan yok)
[ ] Her tipik görev için adım adım akış + ekran görüntüsü
[ ] Alan rehberi: ne/format/zorunlu + NEDEN/otomatik
[ ] HER buton ve event-tetikleyen operasyon açıklı (arka plan sonucuyla)
[ ] Yapılması/Yapılmaması (do/don't) listesi
[ ] Hata/mesaj tablosu: birebir metin + anlam + AKSİYON
[ ] SSS + terim sözlüğü + destek/iletişim
[ ] Teknik terim sızmamış (hepsi sözlükte/sade)
[ ] (KD-F1-01) Klasik/GUI program (tcode'lu Dynpro/ALV) ise → in-system F1-DOCU yardım ayağı ÜRETİLDİ (RE fihrist + TX detay, ZSD000_CL_DOCU runner, ITF ≤72); KD ile senkron; Fiori/UI5 ise muaf (§4.6)
[ ] Key User onayı alınmış
```

## 4.5 KD Numaralandırma ve Dosya Adı
```
No   : KD-[MODÜL]-[SIRA]   (FS-SD-001 ↔ TS-SD-001 ↔ KD-SD-001 aynı geliştirme)
Dosya: KD-[MODÜL]-[SIRA]_[Uygulama_Adı]_v[Versiyon].docx
Örnek: KD-SD-001_Siparis_Kullanici_Kilavuzu_v1.0.docx
```

---

## 4.6 Klasik/GUI Program KD → In-System F1-DOCU Yardım Ayağı (ZORUNLU/VARSAYILAN) *(ID: KD-F1-01)*

> **MUST (KD-F1-01):** Klasik-GUI (Dynpro / ALV / module-pool / report; **tcode ile açılan**)
> bir programın KD'si **İKİ AYAKLIDIR** ve her iki ayak da teslimatın parçasıdır:
>
> 1. **Repo markdown/PDF KD** (`docs/KD-[MODÜL]-[SIRA]_*.md`) — **otorite + offline** başucu
>    kılavuzu; yazım kaynağı ve §4.1-§4.5 kurallarının uygulandığı yer.
> 2. **In-system F1-DOCU yardımı** — **KD içeriğinden türetilen**, kullanıcının programın
>    **içinden** (aşağıda §4.6.2) eriştiği SAP-yerel yardım.
>
> **İkinci ayak VARSAYILANDIR.** Klasik/GUI bir program KD'si hazırlanıyorsa, geliştirici
> **kullanıcı ayrıca istemese de** bu F1-DOCU ayağını otomatik üretir — "söylenirse yaparım"
> DEĞİL, klasik/GUI KD'nin **tanım gereği** bir parçasıdır. (Bu kural tam da *"söylenmeden
> yapılmalı"*yı zorlar; atlandığında KD **eksiktir**.)

**4.6.1 Gerekçe (neden varsayılan).** RAP/Fiori uygulamada yardım UI-içinde/launchpad'de yaşar;
klasik GUI'de kullanıcının başvuracağı **yerleşik** yer SAP-standart **Yardım → Uygulama Yardımı
(F1)**'dır. Repo markdown'ı otorite olsa da son kullanıcı çoğu zaman ona ulaşamaz (dosya paylaşımı
gerekir); programın içinden çıkmadan yardım görebilmesi ancak F1-DOCU ayağıyla sağlanır. Bu yüzden
klasik/GUI KD'de bu ayak opsiyonel bir "ekstra" değil, **varsayılan teslimattır**.

**4.6.2 Mekanizma (özet — tam teslim mekanizması: `../standards/08-classic-gui-f1-help.md`).**
KD-F1-01 **içerik** kuralıdır; **nasıl SAP'ye yazılacağı** std/08'de tanımlıdır. Özet:

- **Teslim yapısı = fihrist + link'li detay** (tek-düz-sayfa değil):
  - **Fihrist** = **`RE` doküman**, obje adı = **programın adı** (ör. `ZSD<NNN>_P_<...>`).
    SAP-standart **RE-DOCU bağı** sayesinde **Yardım → Uygulama Yardımı (F1)** bu dokümanı
    **otomatik açar** — programa **özel buton / fcode / `HELP_OBJECT_SHOW` handler yazmak
    GEREKMEZ** (obje adı = program adı olması yeter).
  - **Detay sayfaları** = `TX` dokümanlar, ad deseni `ZSD<NNN>_KD_<KONU>` (ör.
    `..._KD_AMAC`, `..._KD_SECIM`, `..._KD_KOLON`, `..._KD_IPUCU`); fihristteki
    `<DS:TX....>` link'inden açılır.
- **Altyapı:** proje-ortak generic yazıcı **`ZSD000_CL_DOCU`** (`write_object_doc(...)` →
  `DOCU_UPDATE`) + program-özel bir **`ZSD<NNN>_CL_<...>_DOCU_RUN`** runner (`if_oo_adt_classrun`;
  KD içeriği ITF satırları olarak burada gömülü). Runner sırası: **PROBE → TX detaylar → RE
  fihrist → `DOCU_GET` readback**. Çalıştırma **gateway `adt_classrun`** ile (kullanıcı GUI'de
  hiçbir şey yapmaz). ADT/REST klasik RE/TX doc **yazamaz** — tek yol budur.
- **ITF format (std/08 §3):** her sayfanın **İLK satırı `U1` başlık**; bold = `<ZH>...</>`;
  link = `<DS:TX.<DOCNAME>>görünen metin</>`; **her satır ≤ 72 ham karakter** (tag dahil —
  görüntüleme sınırı; depolama ≤132'ye güvenme, F1'de kuyruk kırpılır); tag'i iki satıra
  BÖLME; **gerçek Türkçe + UTF-8 (BOM yok) + TR login** (ADR 0005-D).

**4.6.3 KD ↔ DOCU türetme ve senkron.** İki ayak **paralel içerik** taşır: repo markdown KD
**otorite/yazım kaynağı**, F1-DOCU ondan **türer**. Her ana KD bölümü (§4.2: Amaç/Kapsam,
Ön Koşullar, Seçim Ekranı, Kolonlar, İpuçları/SSS…) bir DOCU yardım başlığına (bir `TX` sayfası)
eşlenir. **Senkron zorunlu:** KD değişince F1-DOCU **aynı revizyonda** güncellenir (içerik değiştir
+ re-classrun) — biri güncel, diğeri bayat kalamaz. F1-DOCU kaynağı ayrı bir dosyada tutulur:
**`docs/DOCU-[MODÜL]-[SIRA]_<Uygulama>_GUI_Yardim.md`** (SAP'ye yüklenecek ITF kaynak metni;
`KD-[MODÜL]-[SIRA]` ile aynı geliştirmeye bağlı). *(Kanonik örnek: `ZSD001` — tcode ZSD001 →
F1 → fihrist + TX detaylar; generic yazıcı `ZSD000_CL_DOCU`.)*

**4.6.4 İçerik kaynağı (uydurma YASAK).** F1-DOCU metni **repo KD'ye paralel** + tip/değer
tanımları domain fixed-value label'larından **canlı** (`adt_get`), kolon/formül FS + class
mantığından üretilir. Erişim adımlarında **SA38/SE38/SE80 ile program çalıştırma ASLA verilmez**
(std/08 §2; son kullanıcı bunu çalıştıramaz → tcode yoksa yetkiliye yönlendir).

**4.6.5 Denetim (DOC-F1-01 gate).** Bu ayağın **ITF genişlik/format disiplini**
`check_docu_itf_line_width.py` (**DOC-F1-01**) ile denetlenir: DOCU runner'da `iv_line` > 72 ham
karakter veya tag'in tek satırda açılıp-kapanmaması → **BLOCKER** (`run_review.py` pre-flight).
"F1-DOCU ayağı üretildi mi" tamlığı ise §4.4 KD Kalite Kontrol Listesi'nde işaretlenir.

**4.6.6 İSTİSNA.** Bu ayak **yalnız klasik/GUI** program içindir. **RAP + Fiori/UI5 freestyle**
uygulamada F1-DOCU ayağı **YOKTUR** (yardım UI-içi/launchpad'de yaşar) → yalnız repo markdown KD
(+ varsa launchpad yardımı) yeterlidir; std/08 ve KD-F1-01 uygulanmaz.

---

# BÖLÜM 5: FS, TS VE KD ARASINDAKİ İLİŞKİ VE İZLENEBİLİRLİK

## 5.1 Traceability Matrix (İzlenebilirlik Matrisi)

Her FS gereksinimi ile TS teknik çözümü arasında bağ kurulmalıdır:

| FS Gereksinim No | FS Açıklaması | TS Bölümü | TS Nesne/Metod | Test Case |
|-----------------|--------------|----------|----------------|-----------|
| FR-001 | 2 seviyeli onay hiyerarşisi | Bölüm 5.3 | ZCL_SD_ONAY_HANDLER=>APPROVE | TC-001, IT-001 |
| FR-002 | Email bildirimi | Bölüm 5.2 | ZCL_SD_ONAY_HANDLER=>SEND_NOTIFICATION | TC-005 |
| FR-003 | Onay geçmişi raporu | Bölüm 3 (Program listesi) | ZSD_ONAY_RPT | TC-010 |

## 5.2 Döküman Güncelleme Kuralları

- FS değişirse → TS güncellenmeli → Versiyon artırılmalı → Yeniden onay alınmalı
- TS değişirse → FS değişiklik gerektirmeyebilir → Teknik lider onayı yeterli
- Her iki döküman da proje kapanışına kadar güncel tutulmalı

---

# BÖLÜM 6: DÖKÜMAN NUMARALANDIRMA STANDARTLARI

## 6.1 Numara Formatı

```
[TIP]-[MODÜL]-[SIRA]

Örnekler:
  FS-SD-001   → SD modülü 1. Fonksiyonel Spesifikasyon
  FS-MM-012   → MM modülü 12. Fonksiyonel Spesifikasyon
  TS-SD-001   → SD modülü 1. Teknik Spesifikasyon (FS-SD-001'e karşılık gelir)
  TS-FI-003   → FI modülü 3. Teknik Spesifikasyon
```

## 6.2 SAP Modül Kodları

| Kod | Modül |
|-----|-------|
| SD | Sales & Distribution |
| MM | Materials Management |
| FI | Financial Accounting |
| CO | Controlling |
| PP | Production Planning |
| PM | Plant Maintenance |
| QM | Quality Management |
| HR | Human Resources |
| WM | Warehouse Management |
| PS | Project System |
| BC | Basis / Cross-Module |

---

# BÖLÜM 7: KALİTE KRİTERLERİ VE KONTROL LİSTESİ

## 7.1 FS Kalite Kontrol Listesi

```
[ ] Tüm zorunlu bölümler mevcut
[ ] Kapsam dahil ve dışı açıkça tanımlanmış
[ ] AS-IS ve TO-BE süreç diyagramları var
[ ] Tüm iş kuralları numaralandırılmış ve test edilebilir
[ ] Ekran mockup'ları mevcut
[ ] Alan listesi tam ve doğru
[ ] Entegrasyon noktaları belirtilmiş
[ ] Yetkilendirme gereksinimleri tanımlanmış
[ ] Test senaryoları yazılmış
[ ] Müşteri Key User onayı alınmış
[ ] Tüm varsayımlar belirtilmiş
[ ] Kapsam dışı konular açıkça ifade edilmiş
[ ] (İLKE-1) Kullanıcının yazdığı HER istek gereksinim/kural olarak izlenebilir + karşılanmış (hiçbiri düşmemiş)
[ ] (İLKE-2) Danışman katkıları [ÖNERİ] olarak §11-A'da; gereksinime sessizce gömülmemiş; her öneri karara bağlı
[ ] (İLKE-2) Karar-verilemeyen her nokta §11-B'de (seçenek+öneri); "build'de netleşir"e ertelenen fonksiyonel açık nokta YOK
[ ] (§2.0) Kullanıcı-gözü tamlık: boş/mükerrer/max/sıfır girdi, default, teyit/geri-alma, hata gösterimi, "kaydet sonrası ne oluştuğu" görünürlüğü düşünülmüş
```

## 7.2 TS Kalite Kontrol Listesi

```
[ ] FS referansı mevcut
[ ] Tüm geliştirme nesneleri listelenmiş
[ ] Naming convention kurallarına uyulmuş
[ ] DD nesneleri (tablo, domain, element) tam tasarlanmış
[ ] Class/Program tasarımı pseudocode ile açıklanmış
[ ] Performans noktaları değerlendirilmiş
[ ] BAdI/Enhancement yaklaşımı belirtilmiş
[ ] Hata mesajları ve mesaj sınıfı tanımlanmış
[ ] Unit test senaryoları yazılmış
[ ] Transport stratejisi belirlenmiş
[ ] Teknik lider onayı alınmış
[ ] Traceability matrix ile FS'e bağlanmış
[ ] (İLKE-3) FS'teki her FR/KR için TS'te teknik çözüm var (matriste boş satır = eksik TS); iyileştirmeler FS karşılandıktan sonra, FS'i baypas etmeden
[ ] (İLKE-4) §2-A FS Denetimi dolu: her FS maddesi fizibilite/yan-etki/alternatif/hata gözüyle değerlendirilmiş; sorunlular bilgilendirilmiş (kör build YOK)
[ ] (İLKE-5) §11-A "Build-Time Doğrulanacaklar" YALNIZ teknik-teyit içeriyor; fonksiyonel karar sızmamış
[ ] (İLKE-5) Ertelenemez fonksiyonel kararlar kapalı: eşleştirme+çoklu-eşleşme · tüm-key çözümü · dönüşüm (tarih/ondalık/ALPHA/padding) · UoM · entity/child alan-taşıma · edge (boş/mükerrer/max/sıfır) · kilit · hata-birleştirme
[ ] (§3.0) Developer geri-soru simülasyonu yapıldı; satır-1 öncesi her soru TS'te cevaplı ya da (yalnız meşruysa) §11-A'da
```

---

# BÖLÜM 8: SIKÇA YAPILAN HATALAR VE KAÇINILMASI GEREKENLER

## 8.1 FS'te Sık Yapılan Hatalar

| Hata | Açıklama | Doğru Yaklaşım |
|------|----------|----------------|
| Belirsiz gereksinimler | "Sistem hızlı çalışmalıdır" | "Sistem 10.000 kayıtta 3 saniyede sonuç vermeli" |
| Teknik detay | "SELECT * FROM VBAK" | Teknik detaylar TS'te yer almalı |
| Kapsam kayması | Her istek FS'e ekleniyor | Her kapsam değişikliği CR (Change Request) sürecine girmeli |
| Test edilemez kural | "Sistem kullanıcı dostu olmalı" | Ölçülebilir kriterler yazılmalı |
| Onaysız geliştirme | Müşteri imzalamadan geliştirme başlıyor | Önce imza, sonra geliştirme |
| Kullanıcı isteğini gölgeleme | Danışman önerisi kullanıcının açık isteğinin yerine geçiyor/atlıyor | İstek kanon; öneri §11-A'da ayrı, onaya sunulur (İLKE-1/2) |
| Açık noktayı erteleme | "Bunu build'de netleştiririz" | Fonksiyonel açık nokta §11-B soru-setinde kapanır (İLKE-2) |

## 8.2 TS'te Sık Yapılan Hatalar

| Hata | Açıklama | Doğru Yaklaşım |
|------|----------|----------------|
| FS'siz TS | FS olmadan TS yazılması | FS onaylanmadan TS başlatılmamalı |
| Loop içi SELECT | Performans katili | FOR ALL ENTRIES veya JOIN kullan |
| Standart tablo manipülasyonu | VBAK'a direkt INSERT | BAPI_SALESORDER_CREATEFROMDAT2 kullan |
| Hardcoded değerler | Kodda sabit değerler | Customizing tablosu veya sabit tanım |
| Eksik exception handling | TRY-CATCH yok | Her kritik operasyon exception ile sarılmalı |
| Transport sırası hatası | DD olmadan program transportu | Önce DD, sonra program |
| FS'i kör uygulama | Fizibil olmayan/başka yeri bozan/yanlış FS maddesini sorgusuz build | §2-A FS denetimi + bilgilendir + alternatif öner (İLKE-4) |
| Fonksiyonel kararı erteleme | Eşleştirme/dönüşüm/UoM kararını §11-A "doğrulanacaklar"a atma | Meşru teyit ≠ fonksiyonel karar; ikincisi TS gövdesinde kapanır (İLKE-5) |
| Çözümsüz FS maddesi | Bir FR/KR'nin TS karşılığı yok | Traceability matrisinde her FR/KR bir nesne/metoda bağlı (İLKE-3) |

---

# BÖLÜM 9: ŞABLONLAR VE STANDART EKLER

## 9.1 FS Şablonu Dosya Adı Standardı

```
FS-[MODÜL]-[SIRA]_[GELİŞTİRME_ADI]_v[VERSİYON].docx

Örnek: FS-SD-001_Siparis_Onay_Ekrani_v1.0.docx
```

## 9.2 TS Şablonu Dosya Adı Standardı

```
TS-[MODÜL]-[SIRA]_[PROGRAM_ADI]_v[VERSİYON].docx

Örnek: TS-SD-001_ZSD_ONAY_v1.0.docx
```

## 9.3 Döküman Statü Akışı

```
Taslak → İncelemede → Revize Gerekli → Onaylandı → Arşivlendi
                              ↑_______________|
```

---

*Bu döküman SAP danışmanlık projeleri için FS, TS ve KD hazırlama standart rehberidir.*
*Proje gereksinimlerine göre bölümler eklenebilir veya uyarlanabilir.*
*Her proje başlangıcında bu rehber gözden geçirilmeli ve proje standartlarına adapte edilmelidir.*
