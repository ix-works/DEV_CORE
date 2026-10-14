---
applies_to: [s4_private]
layer: L2
scope: project-wide
applies-to: backend
version: 1.0
last-updated: 2026-10-12
status: active
source: "SAP/styleguides — Clean ABAP (CC BY 3.0) özeti; kendi cümlelerimizle, bu evin kararlarına göre AYIKLANMIŞ ve UYARLANMIŞTIR"
---

# Clean ABAP + OO Tasarım — Seçilmiş Alt Küme (stil rehberi, gate DEĞİL)

> **Atıf (CC BY 3.0):** Bu sayfa *SAP/styleguides — Clean ABAP* rehberinden (https://github.com/SAP/styleguides,
> lisans: Creative Commons Attribution 3.0 — https://creativecommons.org/licenses/by/3.0/) **seçilmiş ve değiştirilmiş** bir alt kümedir. Metin rehberden
> kopyalanmamıştır; kurallar bu evin standartlarıyla çeliştiği yerde **ayıklanmış** (§1) ve daraltılmıştır.
> Rehberin tamamı için kaynağa bakın; burada yazılı OLMAYAN bir Clean ABAP kuralı bu evde **bağlayıcı değildir**.

## 0. KAPSAM VE ÖNCELİK (MUST — önce bunu oku)

1. **Yalnız YENİ yazılan ya da bu iş kapsamında DEĞİŞTİRİLEN satıra uygulanır.**
   Mevcut kodu düzeltmek için **gerekçe DEĞİLDİR**: dokunmadığın satırda stil bulgusu açılmaz, "hazır
   açmışken temizleyeyim" toplu düzenlemesi yapılmaz, değiştirdiğin metodun bile **yalnız değiştirdiğin
   satırları** bu sayfaya tabidir. (Gerekçe: stil düzeltmesi davranış değişikliği riski taşır ve
   kapsam/regresyon yükünü işin sahibinden habersiz büyütür.)
2. **Çelişkide mevcut standart ÜSTÜNDÜR.** Öncelik: KESİN YASAKLAR (ADR 0005) > paket `.rules.md` (L4) >
   `02-coding-backend` · `05-coding-rap` · `06-coding-classic-dialog` · ADR 0012 > **bu sayfa**.
   Bu sayfa hiçbir yukarıdaki kuralı gevşetmez ya da daraltmaz.
3. **Gate değildir** (ADR 0019): ihlal reviewer/bug-expert çıktısında `[ÖNERİ]` düzeyindedir; aynı konu
   bir `BE-xx` satırında zaten `HATA` ise o satırın şiddeti geçerlidir.
4. **Test zorunluluğu eklemez ya da kaldırmaz.** Test yazımı std 02 "UNIT TEST" bölümüne ve projenin
   test politikasına tabidir (bazı projeler yeni testi açık onaya bağlar); §2 CLN-13 yalnız test yazılan
   işte uygulanır.

## 1. AYIKLANAN NOKTALAR — Clean ABAP önerir, bu evde GEÇERLİ DEĞİLDİR

| # | Clean ABAP önerisi (özet) | Bu evdeki kural | Nerede |
|---|---|---|---|
| A1 | Hata bildiriminde dönüş kodu değil yalnız istisna | **Daraltıldı:** yeni OO iç mantıkta istisna tercih edilir; ama BAPI/FM/RFC arayüzünde `BAPIRET2`, RAP/EML'de `failed`/`reported` **korunur** — sınırda çevirici katman mesajı taşır, yutmaz | std 02 "BAPI Return Handling" · std 10 · BE-53 · BE-78 |
| A2 | Test edilebilirlik için constructor injection / test double varsayılan tasarım | **Alınmadı** — varsayılan tasarım test-double'a göre şekillenmez; test yazımı std 02 + proje test politikasına tabidir | §0 madde 4 · §3 "Alınmayanlar" |
| A3 | Liste çıktısında `CL_SALV_TABLE` tercihi | **Alınmadı** — ALV aracı seçimi std 06 §3'ün senaryo tablosuna ve kanonik şablona (ADR 0012) bağlıdır | std 06 §3 · ADR 0012 |
| A4 | Ad ön-eki (`lv_`, `lt_`, `gs_` …) kullanmama | **Alınmadı** — ön-ekler bu evde zorunludur | std 06 §6 · std 01 |
| A5 | `DEFAULT KEY`'den kaçın + tek sonuçta `RETURNING` | **Birlikte yazılır:** `RETURNING` tercih edilir **ama** dönen tablo tipi TAM TİPLİ olmalıdır (key ifadesi şart — BE-57); `WITH EMPTY KEY` seçilirse ölçütsüz `SORT`/`DELETE ADJACENT DUPLICATES` anlamsızdır. Yeni tipte anahtarı bilinçli seç; key'siz tip yazma | BE-57 · BE-72 |

## 2. ALINAN KURALLAR (yeni/değişen satır için)

| ID | Kural | Bu evdeki ek şart / tuzak |
|---|---|---|
| **CLN-01** | Mantıksal değer `abap_bool` + `abap_true`/`abap_false`; koşuldan değer üretmek için `xsdbool( )` | — |
| **CLN-02** | Değişkeni ilk kullanıldığı yerde satır içi bildir (`DATA(...)`, release izin veriyorsa `FINAL(...)`) | ⚠ Döngü içinde **sayaç/bayrak/biriktirici** için satır içi bildirim YAZMA — her turda sıfırlanmaz (BE-50) |
| **CLN-03** | Tek sonuç → `RETURNING`; az sayıda `IMPORTING` parametresi; davranışı ikiye ayıran mantıksal giriş parametresi yerine iki metot | `RETURNING` tipi tam tipli (BE-57). Biriktirilen tabloyu `EXPORTING` ile döndürme — hedefi temizler (BE-78) |
| **CLN-04** | Sihirli sayı/dize yerine sabit | Zaten std 06 §6 — oraya bak |
| **CLN-05** | Koşulu olumlu yaz; `IS NOT` biçimi; erken `RETURN` ile koruma cümlesi; tek değişken üzerindeki uzun `ELSEIF` zinciri yerine `CASE` | — |
| **CLN-06** | Tablo türünü erişim desenine göre seç (STANDARD/SORTED/HASHED); varlık sorgusu `line_exists( )`; SORTED/HASHED'e `INSERT … INTO TABLE` | A5 satırı · FAE öncesi boş tablo kontrolü `playbook/coding-patterns.md` §24 |
| **CLN-07** | Dize birleştirmede şablon `\|…\|`; teknik literal için backtick | Kullanıcıya görünen metin literal DEĞİL: text pool / mesaj sınıfı (std 06 §5, ADR 0005-D). Şablonda `\|` kaçışı BE-47 · `concat` boşluk tuzağı BE-59 |
| **CLN-08** | Yorum **neden**i anlatır; yorum satırına alınmış kod silinir (tarih git'te) | Yorumun KONUMU SAP kaydetme kuralına tabidir — `playbook/adt-classes.md` §24.10 bu sayfanın önündedir |
| **CLN-09** | Metot tek iş yapar, kısa ve tek soyutlama düzeyindedir | Büyüklük sezgisi §3 OO-2 |
| **CLN-10** | Modern ifadeler (`VALUE`, `CORRESPONDING`, `COND`, `SWITCH`, `FOR`, `REDUCE`) eski deyimlere tercih edilir; eskimiş deyim (`MOVE … TO`, `COMPUTE`, statik `CALL METHOD`) yeni satırda yazılmaz | ⚠ EML/kaynak-tabanlı sınıfta abaplint ayrıştırıcısı modern söz dizimini tam okuyamaz → **canlı sözdizimi denetimi zorunlu** (bug-checklist-backend "MODERN-SYNTAX" notu); hesaplı alt-dize uzunluğu BE-36; `PERFORM` aktüeli BE-41; NUMC literali BE-80. Klasik dialogda `FORM` kullanımı std 06 §1-2'ye tabidir — bu satır onu değiştirmez |
| **CLN-11** | Düzenli ifadeden önce yerleşik dize fonksiyonları | PCRE çıplak boşluk tuzağı BE-81 |
| **CLN-12** | Statik sınıf yerine durum taşıyan iş için örnek (instance) metodu; üyeler varsayılan `PRIVATE` | §3 OO-1 |
| **CLN-13** | *(Test yazılan işte)* test metodu adı davranışı söyler; düzen **verilen–yapılan–beklenen**; yalnız açık (public) davranış test edilir | Aktivasyon sonrası ilk koşuda sahte "0 test" görülebilir — beklenen test sayısı rapora yazılır |

**Otomatik kontroller (Clean ABAP'ın önerdiği araçların bizdeki karşılığı):** ATC Priority-1 zorunlu
(BE-12) · `scripts/validators/check_abaplint.py` · pretty printer (`playbook/adt-classes.md`). ⚠ "0 bulgu"
yalnız aracın baktığı yüzeyde temizlik demektir (CLAUDE.core §7 KAPSAM BEYANI) — bu sayfanın kurallarının
çoğunu hiçbir araç ölçmez.

## 3. OO TASARIM ALT KÜMESİ

| ID | Kural | Not |
|---|---|---|
| **OO-1** | Sınıf varsayılan `FINAL`; kalıtım yerine **bileşim** (sınıf içinde başka sınıfın örneğini kullan) | Kalıtıma açık sınıf bilinçli bir tasarım kararıdır — TS'te gerekçesi yazılır |
| **OO-2** | Tek sorumluluk. "Her şeyi bilen sınıf" sezgisi: ~5'ten çok açık metot ya da ~800 satırı aşan sınıf **tartışma sinyalidir**, sınır değildir | Ortak (paylaşılan) sınıfları şişirmeme gerekçesi ADR 0012 ile aynıdır |
| **OO-3** | **YAGNI** — desen ihtiyaç doğmadan uygulanmaz. Varsayılan cevap "uygulama"dır (aşağıdaki tablo) | ADR 0012 "önce şablon, soyutlama sonra" ruhu |
| **OO-4** | Arayüz-önce (açık API'yi `IF_`/`ZIF_` arkasına koymak) **yalnız birden çok tüketicisi olan global ortak sınıflarda** önerilir | Klasik dialog programının lokal sınıflarına (std 06 §2 `LCL_*`) dayatılmaz |

**Desen ne zaman uygulanır — varsayılan "UYGULAMA":**

| Desen | Uygula, eğer… | Uygulama, eğer… |
|---|---|---|
| Factory | yaratılacak sınıf çalışma anında birden çok somut türden seçiliyorsa | tek somut tür var ve öngörülebilir ikinci tür yoksa |
| Strategy | aynı işin **bugün** ikiden çok değişkeni var ve seçim veriyle yapılıyorsa | tek `CASE` dalı yeterliyse (paket `.rules.md` dal/metot düzeni öngörüyorsa o geçerlidir) |
| Observer | bir olayın birden çok, birbirini bilmeyen dinleyicisi varsa | tek dinleyici varsa — doğrudan çağrı |
| Adapter | dış arayüz (BAPI/RFC/OData) iç modele çevrilecekse — sarmalayıcı sınıf | çağrı tek yerde ve çeviri yoksa |
| Decorator | davranışa çalışma anında katman eklenmesi gerçekten gerekiyorsa | ek davranış sabitse — doğrudan metot |

**Alınmayanlar (bilinçli):** test izolasyonu için constructor injection, `CREATE PRIVATE` + fabrika ve
test double (`cl_abap_testdouble`) **varsayılan tasarım olarak** alınmadı (§1 A2). Somut bir test
gereksinimi doğarsa o iş kapsamında ayrıca değerlendirilir.

## 4. İlgili

- L1b kısa işaretçi: [`../claude/rules/abap-clean-code.md`](../claude/rules/abap-clean-code.md) (`.abap` okununca yüklenir)
- [`02-coding-backend.md`](02-coding-backend.md) · [`05-coding-rap.md`](05-coding-rap.md) · [`06-coding-classic-dialog.md`](06-coding-classic-dialog.md) · [`10-standart-veriye-yazma-api-secimi.md`](10-standart-veriye-yazma-api-secimi.md)
- [`../playbook/checklists/bug-checklist-backend.md`](../playbook/checklists/bug-checklist-backend.md) — ölçülmüş tuzaklar (bu sayfanın önündedir)
- prior-art: yok (2026-10-12 — core `standards/` · `playbook/` · `claude/rules/` · `governance/decisions/` altında "clean abap" 0 eşleşme; dağınık karşılıklar §1-§2'de satır satır bağlandı)
