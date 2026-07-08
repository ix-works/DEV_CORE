# Operasyonel Tuzaklar — SAP ADT (<PROJECT_NAME> konvansiyonu)

Bu dosya, SAP'ye yazmadan önce bilinmesi gereken tekrar-eden tuzakları toplar.
Kaynak: proje playbook'u (`playbook/adt-*.md`) + NTT marketplace `sap-adt` skill'inden
süzülen, bizim kurallarımıza (ZSD001_CLC, TR-zorunlu, MCP-önce) uyarlanmış dersler.
Detaylı, sistemde-kanıtlanmış REST şablonları için `playbook/adt-foundation.md`'ye bak.

---

## 1. TR master-language ile obje yaratma (ADR 0005 §D)

SAP, `adtcore:masterLanguage="TR"` body attribute'unu ve `sap-language` header'ını
**görmezden gelir**. Z obje TR dilde yaratılsın diye tek çalışan yöntem:

- Login isteğinde (`GET /sap/bc/adt/discovery`) `sap-client` ve `sap-language=TR`
  **aynı istekte, query param** olarak verilir.
- Daha önce EN olarak yaratılıp silinmiş bir isim, metadata önbelleği yüzünden tekrar
  **EN** gelir. Çözüm: test ismiyle yarat → TR doğrula → sil → asıl isimle yarat.
- Her CREATE için **ayrı session** aç — aynı session'da arka arkaya yaratılan objelerde
  SAP ilkini TR, sonrakileri EN yapabilir.
- Activate'ten önce REST GET ile `adtcore:masterLanguage="TR"` ve 4 label dolu mu doğrula.

> MCP `sap-adt` tool'ları create'i EN yaratabilir (bkz. memory: MCP EN master-lang
> uyarısı). Z obje yaratırken raw REST + TR + post-create doğrulama tercih et.

## 2. Transport disiplini

Aktif transport: **`<TRANSPORT>`** (kullanıcı verir, AI yaratmaz — ADR 0005 §C).

- Numarayı **uydurma**, hafızadan/önceki context'ten **alma**, her seferinde teyit et.
- **Hata mesajındaki transport numarasını ASLA kullanma.** "object already in
  FIDKxxxxxx" mesajındaki numara başka geliştiriciye ait olabilir; kullanmak değişikliğini
  onun request'ine enjekte eder. DUR ve kullanıcıya sor.
- **409 / lock conflict → retry YOK.** Her retry yeni boş K-type transport (ghost task)
  yaratır. Sıra: kullanıcıya bildir → SM12 stale lock temizle → SE10 doğru transport'a
  assign → tek retry.
- `push` başarılı olunca SAP otomatik S-type child task yaratır (K-type altında) —
  bu normaldir, beraber release olur.

## 3. Windows encoding ve yol

- Konsol `cp1252` → Unicode basamaz. Python `print()` **ASCII-only**: `[OK]`, `[FAIL]`,
  `[WARNING]`, `[INFO]`; ok/bullet yerine `to`, `from`, `-`, `*`.
  Pattern: `safe = lambda t: t.encode('ascii', 'replace').decode('ascii')`.
- Windows yolları **raw string**: `r'<PROJECT_ROOT>'`.
- PowerShell: `$null` (not /dev/null), `$env:VAR`, backtick devam.

## 4. Aktivasyon notları

- `syntax_check` bazen **yanlış hata** raporlar (özellikle CDS/class etkileşimi);
  gerçek aktivasyon başarılı olabilir — aktivasyon sonucu (`type="E"`) esastır.
- Aktivasyon program load'u yazar ama çalışan ABAP server class buffer'ını flush
  etmeyebilir. Runtime'da değişiklik görünmüyorsa: Eclipse/SE24'ten re-activate veya
  SM04'te `/$ABAP_BUFFER_RESET` (load-balanced sistemde her app server'da).
- DDIC objeleri lock istemez: create/change → activate. Class/program/FM: lock → push
  → activate → unlock (unlock'u finally'de garanti et).
- MCP `_activate_and_verify` artık `adtcore:version="active"` kontrol eder — varlık
  değil, aktiflik doğrulanır.

## 5. ABAP pitfall'ları (üretmeden önce)

- **Class/obje adı > 30 karakter** → SAP sessizce keser, aktivasyon bozulur.
- Statement sonu **nokta** (`.`), noktalı virgül değil.
- `OBLIGATORY` sadece selection-screen için geçerli, class IMPORTING param için değil.
- Sistemde olmayan tipler (örn. eski sürümde EPST/PRDHA/VORGANG) → önce var mı doğrula.
- `CONDENSE` TYPE string ister, `lines()` dönüşü TYPE i ile uyumsuz.
- `TEXT-xxx = '...'` ile değiştirme — selection-screen title/comment için serbest
  değişken (`tit1`, `com01`) kullan, `INITIALIZATION`'da ata.

## 6. Idempotent create ve silme

- Create "already exists" / 409 → **başarı say**, push'a devam.
- Silme onaysız YAPILMA. DDIC (domain/dtel/struct/CDS) → direkt HTTP DELETE;
  class/interface/program → lock'lu delete; tablo → SE11 (kullanıcı). Where-used temiz olmadan silme.

## 7. SQL son çare (ADR 0005 §B)

Veri okuma için bile önce CDS data-preview / BAPI / RFC tercih et. Zorunlu `SELECT`
varsa: ABAP SQL farkları → `ORDER BY ... DESCENDING`, `table~column` (tilde),
`UP TO n ROWS` (LIMIT değil), boolean `'X'`/`' '`, statement sonu noktasız.
Veri **yazma** için direkt SQL **yasak**.
