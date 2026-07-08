---
adr: 0005
title: SAP Standart Obje Koruma + Sistem State Müdahale Yasakları
status: accepted
date: 2026-05-14
priority: KRİTİK — BYPASS EDİLEMEZ
deciders: <SAP_USER>
supersedes: —
superseded-by: —
---

# ADR 0005 — SAP Standart Obje Koruma + Sistem State Müdahale Yasakları

> ⛔ **Bu ADR'deki kurallar HİÇBİR şekilde bypass edilemez.** İstisna yok. Şüphe varsa kullanıcıya sor, kendi başına işlem yapma.

## Bağlam

AI agent'lar (Claude Code dahil) SAP ADT REST API üzerinden hızlıca obje yaratma/değiştirme/silme yapabiliyor. Bu güç, dikkatsiz kullanılırsa **SAP sisteminin temelini bozar**:

- Standart objeye dokunulması → SAP upgrade'lerde değişikliklerin kaybı, customizing çakışması, sistem destek dışı kalma
- Standart tablo verisine direkt insert/update/delete → tutarsız master/transactional data, business logic bypass
- Transport request manipülasyonu → upstream sistemlere yanlış değişiklik akışı, release karmaşası
- Package yaratma → namespace karmaşası, NTTDATA standardı bozulması

Bu kuralları **doküman olarak söylemek yetmez** (LESSONS_LEARNED #4); **kurallar her yerde, her oturumun en üstünde, en görünür yerde** olmalı.

## Karar — Kesin Yasaklar Listesi

### KATEGORİ A — SAP Standart Objelere Müdahale (Z ile başlamayan TÜM objeler)

**Operasyon türünden bağımsız YASAK:**

| # | Yasak |
|---|---|
| A1 | Standart **tablo** yaratma/değiştirme/silme (örn. LIKP, LIPS, VBAK, VBAP, VBPA, MARA, MARC, KNA1, KNVP, T100, vb.) |
| A2 | Standart tabloya **append struct** ekleme veya append struct alan değiştirme |
| A3 | Standart **struct/view/data element/domain** değiştirme veya alan ekleme |
| A4 | Standart **program/include/class/method/FM/BAdI/enhancement spot** değiştirme |
| A5 | Standart **function module** implementasyonunu değiştirme veya enhancement implementation yazma |
| A6 | Standart **BAdI**'nin **standart implementasyonunu** değiştirme/yazma = YASAK. *(Yeni **Z\* BAdI** implementasyonu serbesttir = izin verilir — bu satır YALNIZ standart impl'i kapsar; Z\* prefix + kendi enhancement implementation'ın.)* |
| A7 | Standart **customizing tablosu (T-tables)** değişiklik (örn. T001, T024, T077Y, vb.) |
| A8 | Standart **message class** değişikliği veya yeni mesaj ekleme |
| A9 | Standart **CDS view** veya **DDIC view** değiştirme |
| A10 | Standart **transaction code** değiştirme |
| A11 | Bu değişiklikleri yapan **script yazma veya çalıştırma** — script aracılığıyla bypass YASAK |
| A12 | Append struct, custom field, DTEL adı **AI tarafından önerilmez ve uygulanmaz**. Kullanıcı SAP GUI'den belirler ve uygular, sonucu (field adı, DTEL adı, domain) AI'a bildirir. AI sadece bu sonucu Z'li objelerinde kullanır. |
| A13 | "Geçici", "test için", "bir kerelik" istisna **YASAK** — standart objeye dokunma kararı her zaman kullanıcının |

### KATEGORİ B — Standart Tablo Verilerine Direkt Müdahale

| # | Yasak |
|---|---|
| B1 | Standart tablo'ya direkt **INSERT** (örn. `INSERT INTO VBAK VALUES ...`) |
| B2 | Standart tablo'ya direkt **UPDATE** (SAP standart fonksiyonu bypass eden) |
| B3 | Standart tablo'dan direkt **DELETE** veya **MODIFY** |
| B4 | SQL/ABAP üzerinden standart business logic'i bypass ederek veri yazma |
| B5 | **Z'li programda yazdığın ABAP kodunda** standart tabloya direkt INSERT/UPDATE/MODIFY/DELETE — kendi yazdığın Z* programı içinde olsa bile YASAK |
| B6 | Aşağıdaki **ZORUNLU akış** (BAPI→RFC FM→BDC) tükendiyse direkt-SQL / business-logic-bypass **İCAT ETME** → kullanıcıdan manuel iste. *(BDC/RFC aramak "icat" DEĞİL — kanonik akışın parçası; "icat" = akış-dışı bypass çözüm.)* |

**ZORUNLU akış:** Önce SAP standart **BAPI** ara (`BAPI_*_CREATE`, `BAPI_*_CHANGE`), bulamazsan **RFC FM** ara, bulamazsan **transaction (BDC)** ara, hâlâ bulamazsan kullanıcıdan manuel yapmasını iste. Asla direkt SQL yazma.

### KATEGORİ C — Sistem State Yönetimi

| # | Yasak |
|---|---|
| C1 | **Transport request yaratma** (`/sap/bc/adt/cts/transportrequests` POST veya benzeri) |
| C2 | Var olan **transport request'i release etme** (CTS_API_RELEASE_REQUEST vb.) |
| C3 | **Package yaratma** (SE21 POST veya `scripts/create_package.py` çalıştırma) |
| C4 | **Username/lock** silme (kullanıcının enqueue lock'ları) |
| C5 | **System change option** değiştirme |

### KATEGORİ D — Z'li Obje Yaratırken/Değiştirirken Zorunlular

Z* (custom) objelerle çalışırken **zorunlu davranışlar**:

| # | Zorunlu |
|---|---|
| D1 | SAP'ye **TR (Türkçe) login** ol — `sap-language=TR` (yoksa metinler boş kalır, downstream'de hatalar) |
| D2 | Obje'nin **deskripsiyonu/title'ı TR olarak DOLU** yarat |
| D3 | Tüm **label/heading/short/medium/long** field text'leri **TR olarak TAM** yaz (4 label) |
| D4 | Message class mesajları **TR olarak yaz** (selfexplanatory veya açıklamalı) |
| D5 | DTEL'in 4 field label'ı (short=10, medium=20, long=40, heading=55) **boş bırakılmaz** |
| D6 | CDS view'ın `@EndUserText.label` annotation'ı **TR olarak DOLU** |
| D7 | Class/method dokümantasyonu (varsa) TR |
| D8 | Activate ÖNCE doğrula: label'lar gerçekten kaydedildi mi? (REST GET ile kontrol) |

## Yapılması GEREKİYORSA Operatöre Sorma Protokolü

Bir geliştirme için yukarıdaki yasaklardan birini yapma ihtiyacı doğarsa:

1. **DURDUR** — Otomatik yapma
2. **AÇIKLA** — Neden gerekli? Hangi obje? Hangi alan?
3. **ÖNERİ SUN** — Alternatifler var mı? (Append yerine custom field, custom tablo, vb.)
4. **KULLANICIDAN İSTE** — "X yapmam gerekiyor çünkü Y, alternatif Z ama uygun değil. SAP GUI'den siz yapar mısınız?"
5. **SONUCU BEKLE** — Kullanıcı yapınca obje adını/değişiklik notunu sana iletir
6. **DEVAM ET** — Yeni durum üzerine kendi (Z'li) işine devam et

**AI HİÇBİR ŞEKİLDE** "küçük bir dokunuş, kullanıcı fark etmez" şeklinde standart objeye dokunmaz.

## Gerekçe

- **Standart objeler upgrade-safe** olmalı — değişiklik → upgrade sırasında kayıp veya çakışma
- **Standart verilerin business logic'i** vardır — bypass etmek tutarsızlık yaratır (numara aralıkları, status update'leri, accounting belgeleri)
- **TR not enforcement** olmadığı için unutuluyor — sistemde İngilizce/boş label'lar kalıyor, EUM (End User Maintenance) sırasında SAP "label yok" diyor, kullanıcı manuel girmek zorunda kalıyor
- **Transport/Package yaratma** projeye özel kararlar — AI her gördüğüne bir paket/TR açarsa karmaşa olur

## Sonuçlar

- ✅ AGENTS.md ve CLAUDE.md başına KESİN YASAKLAR bloğu eklenmeli (her oturum ilk gördüğü)
- ✅ README.md "Önemli Kurallar" bölümünde belirgin yer
- ✅ Session başlangıç teyidi template'ine "yasaklar aktif" satırı
- ✅ Bu ADR'ye AGENTS.md ve CLAUDE.md'den link
- ❌ Tek seferlik istisnaya kapı açan dil kullanılmaz ("genelde", "çoğunlukla", vb.)
- ❌ Validator/script bu yasakları otomatik enforce edemez (SAP-side detection gerekir) — sadece doküman + AI disiplini

## Enforcement

| Katman | Mekanizma |
|---|---|
| **Doküman** | AGENTS.md §0 (en üst), CLAUDE.md §0 (en üst), README.md |
| **Session loader** | Ekran teyidi template'inde "⛔ KESİN YASAKLAR aktif" satırı |
| **AI davranışı** | Trigger phrase yakalama (lessons-learned.md): "standart objeye dokunabilir misin", "tabloya alan ekle", vb. → STOP |
| **SAP-side (operatör)** | Standart objeler için SAP'de değişiklik yetkisi vermeme (RFC kullanıcısı) |

## İlgili

- [`../../AGENTS.md`](../../AGENTS.md) §0 — kesin yasaklar
- [`../../CLAUDE.core.md`](../../CLAUDE.core.md) §0 — session ilk yüklenen
- [`../../playbook/lessons-learned.md`](../../playbook/lessons-learned.md) — Pattern #5 (Trust without Verify) ile ilgili
- [`0003-layered-rule-architecture.md`](0003-layered-rule-architecture.md) — L1 katmanda yer
