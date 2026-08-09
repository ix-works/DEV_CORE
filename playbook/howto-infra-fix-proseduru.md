---
applies_to: [all]
---

# HOWTO — İnfra-Fix Prosedürü: DONDUR → SINIFLA → (EXPRESS | KUYRUK) → İNFRA-EXPERT

> **Tetik:** validator hatası/yanlış-pozitif · hook bozuk/bloklamamalıydı · guard FP · script/MCP bug'ı · checklist-kuralı yanlış · "kuralı gevşetelim/değiştirelim" dürtüsü · gate beni haksız blokladı.

> **Problem sınıfı:** Görev sırasında paylaşılan altyapıda (hook/validator/MCP-script/rules/
> standards/checklist/CI/ajan-tanımı/şablon = "İNFRA") sorun görülünce, o anki görevin DAR
> bağlamıyla yapılan nokta-fix başka bağlamları kırar. Resmî adı: *test-tampering/reward-hacking*
> dürtüsü (Anthropic araştırması: kendi haline bırakılırsa genelleşir). Teknik öz-koruma
> harness'ta KIRIK (anthropics/claude-code#11226: hook'lar kendini koruyamaz) → çözüm zorunlu
> olarak PROSEDÜR + görünürlük + doğru-anda-hatırlatma (JIT-recall).
> **Kural revizyonu (2026-08-01, kullanıcı onaylı):** "araç/kod fix = lider'in işi" kuralı
> evrildi — *fix'in SORUMLULUĞU ve SON SÖZÜ liderde; kuyruk-fix'lerinin ÜRETİMİ taze-spawn
> infra-expert'te* (gateway-paradigmasının infra'ya uygulanması).

## KİM NE YAPAR (özet tablo)

| Adım | Sahip |
|---|---|
| 0-1-2: Fren + sınıflama + express/kuyruk kararı + EXPRESS fix'ler | **LİDER** |
| 3: Kuyruk fix-seansı (F1-F5, üç-bağlam test, fixture) | **infra-expert** (taze spawn, worktree) |
| Diff-review + testlerin bağımsız koşumu + commit/PR + kullanıcı-onay akışı | **LİDER** |
| META-İNFRA (ajan tanımları, `.claude/settings*`, hook_shim, damga-zinciri) | **YALNIZ LİDER** (döngü-yasağı: kendi guardrail'ini düzelten ajan = başladığımız problem) |

Alt-ajanlar (gateway/expert'ler) için değişen bir şey YOK: infra'ya dokunmaz, raporlar (Zone-A).

## ADIM 0 — REFLEKS FRENİ
İnfra-sorunu görüldüğü AN varsayılan: **DONDUR** — görev bağlamında infra DEĞİŞTİRİLMEZ.
(O anki bağlam tanım gereği dardır; "geçmek için değiştirme" dürtüsü ölçülmüş risktir.)

## ADIM 1 — SINIFLA (≤2 dk; kontrol-grubu ZORUNLU — PATTERN #19)
Bilinen-iyi bir vakayla kıyasla, dört sınıftan birine koy:
- **K1 — Yanlış kullanım** (arg/format/sıra/ön-adım): infra'ya dokunma; kullanımını düzelt (öğretiyse T1).
- **K2 — Yanlış-pozitif** (kural doğru, vakan meşru istisna): bypass ARAMA; FP-kaydı kuyruğa (FP = kuralın kalite-verisi).
- **K3 — Gerçek infra-bug** (bilinen-iyi vaka da düşüyor): kanıt paketiyle Adım 2.
- **K4 — Kural içeriği eskimiş/eksik** (davranış-KARARI): daima KUYRUK.

## ADIM 2 — YOL AYRIMI (hız buradan gelir)
**⚡ EXPRESS ŞERİT (S0-infra; LİDER, görev-içi)** — DÖRDÜ BİRDEN sağlanmalı:
① mekanik hata (typo/kırık-yol/yanlış-değişken/eksik-import) — davranış-kararı YOK ·
② blast-radius grep'le tek-nokta kanıtlı · ③ mevcut fixture/negatif-test ≤1 dk'da YEŞİL ·
④ hiçbir kuralı GEVŞETMİYOR. → fix + test + **AYRI commit** (`infra-fix(S0): ... — <görev> sırasında`).

**📥 KUYRUK (varsayılan)** — proje `governance/infra-findings.md`'ye tek-satır kayıt:
`tarih | bileşen | semptom | kontrol-grubu-sonucu | sınıf K1-K4 | görev-bağlamı | önerilen-yön?`
Görev DEVAM eder. Workaround gerekiyorsa bypass DEĞİL (skip_reviewer vb. YASAK); meşru
alternatif yoksa kullanıcıya eskalasyon. Kuyruk-eskalasyonu: content-health-radar turu açık
kayıtları tarar (süresiz-açık kayıt = karantina-çürümesi; flaky-quarantine literatürü).

## ADIM 3 — İNFRA-EXPERT FIX-SEANSI (kuyruktakiler)
**Lider hazırlar:** ① worktree açar (`git -C <core> worktree add <yol> -b infra/<konu>`) —
ajan CANLI çekirdeğe asla yazmaz (junction-anında-yayılım riski fiziksel olarak sıfır) ·
② R2-brifing: kuyruk-kaydı + ilgili lessons/removed-controls + worktree-yolu + kapsam-sınırı.
**infra-expert üretir (tanımındaki zorunlu beşli):**
- **F1 Blast-radius:** bileşeni kim kullanıyor (grep + settings-matcher + çağıran-zincir + kaç proje).
- **F2 Kök-soru:** nokta-vaka mı SINIF mı? Fix SINIFI çözmeli; vaka-özel istisna = son çare + gerekçeli.
- **F3 Üç-bağlam testi:** bilinen-bozuk→FAIL + bilinen-temiz→PASS + **görev-DIŞI üçüncü vaka** —
  fixture'lar `tests/fixtures/`e KALICI eklenir (G1 korpusu).
- **F4 Gevşetme-cetveli:** kapsam/eşik DARALIYORSA raporda **⚠GEVŞETME bayrağı** zorunlu +
  FP-kanıtı; bu sınıf yalnız KULLANICI onayıyla merge edilir + `removed-controls.md` kaydı.
- **F5 Yayılım-notu:** çift-katman etkisi (template/overlay/senkron) + DoD maddeleri.
**Lider kapatır:** diff-review → testleri BAĞIMSIZ yeniden koşar → (GEVŞETME varsa kullanıcı
onayı) → commit/PR → yayılım adımları → kuyruk-kaydını KAPANDI işaretler.

## "TAZE BAĞLAM" NE DEMEK (sık soru)
Kişi değil, ÜÇ ŞEY değişir: **zaman/iş-birimi** (görev-diff'inden ayrı) · **girdi-seti**
(dar semptom değil; kuyruk-kaydı + F1'in YENİDEN yaptığı geniş bakış — görev-anı bağlamı
bilinçli masada değil) · **hedef** ("işim geçsin" değil "bileşen TÜM kullanıcıları için doğru
olsun"; F3'ün üçüncü vakası tam bunu zorlar). Bug-expert'in taze-spawn ilkesiyle aynı mantık —
infra-expert bunu spawn-fiziğiyle sağlar.

## DAYATMA KATMANLARI (bilinçli hafif — #11226 nedeniyle sosyal+görünürlük)
Bu dosya + CLAUDE.core §1.1 atfı · JIT-recall indeksi (howto başlıkları — sorun anında
prompt'a düşer) · post_tool_failure merdiven-satırı · bug-checklist "kapsam-dışı infra
değişikliği" maddesi (BE-66/FE-39) · radar-turu kuyruk-eskalasyonu.
**OPSİYONEL (ayrı onay, İZLE'de):** ConfigChange hook'unu izleme→BLOK moduna almak ·
CODEOWNERS+branch-protection (T7 adayı).

## SAHA DERSLERİ — 2026-08-01 kuyruk turundan (infra-expert'lerden terfi)

### D1 — Brifingdeki TEŞHİS kanıt değil, HİPOTEZDİR
Lider brifinginin *"şu bozuk, şu taraf doğru"* cümlesi bir hipotezdir. Fix'e başlamadan
önce iddiayı **kendi kontrol grubunla** ölç; ölçüm hipotezi çürütürse fix'in **yönünü
değiştir** ve raporda açıkça *"brifingdeki yön tersti"* de.

*Vaka:* bir kayıt "gerçek klasör adları alt çizgiyi KORUYOR → A yanlış, B doğru" diyordu ve
kanıt olarak bir dizin adı gösteriyordu. Ölçüm: o dizinde aracın kendi yazdığı hiçbir iz
yoktu — onu **bizim script'imiz** yaratmıştı. **Dairesel kanıt:** bir aracın konvansiyonunu,
o araca ait sanılan *kendi çıktımızla* doğrulamak. Gerçek yer-doğrusu bulunduğunda yön
tersine döndü; brifing uygulansaydı çalışan üç tüketici bozulup bozuk ikisi kanonik ilan
edilecekti.

**Nasıl uygulanır:** iddia "X doğru, Y yanlış" diyorsa X ve Y'yi AYNI harness'ta aynı
girdiyle koştur ve **skoru yaz** ("A 4/4, B 2/4"). Kanıt olarak gösterilen artefaktın **kim
tarafından üretildiğini** sor — bizim aracımız ürettiyse kanıt değeri sıfırdır. Ölçmek
mümkün değilse `DOĞRULANAMADI` işaretle, tahminle ilerleme.

### D2 — Fixture ÇÖKMEMELİ, ÖLÇMELİ (mutasyon-dostu tasarım)
F3'te yazdığın fixture iki şeyi baştan sağlamalı:

1. **Mutasyon dostu:** fix-ÖNCESİ koda karşı koşulduğunda **çökmemeli**, kaç vektörün
   düştüğünü **ölçmeli**. İmza değiştiyse (`list` → `(list, list)`) çağrıyı tolere eden bir
   sarmalayıcı koy; ana kodu çağıran yerleri `try/except` ile "ölçülen sonuca" çevir. Yoksa
   mutasyon `Traceback + exit 1` verir ve **hangi vektörün ayırt edici olduğu görünmez** —
   üstelik `2>/dev/null` ile koşulursa "0 FAIL" diye okunur ve *korpus ölçüyor* sanılır.
   ⚠ **Çökme ≠ FAIL** kuralı mutasyon testinde de geçerlidir: mutasyon 0 FAIL verdiğinde
   ÖNCE fixture'ın gerçekten koştuğunu kanıtla (çıkış kodu + `2>&1`).
2. **Ortam/locale bağımsız:** davranış testi makinenin locale'ine bağlıysa CI'da sessizce
   boşalır. Nedenselliği açıkça kur (ör. bozuk kodlamayı **kendin yaz**, "makine öyleyse"
   deme) ve mümkünse yapısal bir AST çapası ekle (açık `encoding=` var mı).
3. **Mutasyon koşucusu fixture'ın İÇİNDE yaşar** (2026-08-09): çalışan kodu `git show … >`
   ile EZİP geri almak yerine fixture'a `--mutasyon [--ref <sha|ref>]` bayrağı koy →
   `git show <ref>:scripts/<modül>.py` geçici dosyaya, `importlib.util.spec_from_file_location`
   ile **ayrı adla** yükle, AYNI vektörleri koş. Kazanç: çalışma ağacı hiç kirlenmez, sayı
   **tekrar üretilebilir** olur (rapora "18/18 → 9/18" diye yazılır ve okuyan doğrulayabilir),
   "geri almayı unutma" sınıfı tümden kapanır. ⚠ Eski sürümde **olmayan** parametre/metot
   `TypeError`/`AttributeError` verir → koşucu çöker → mutasyon "0 FAIL" gösterir (yukarıdaki
   *çökme ≠ FAIL*): imzayı `inspect.signature` ile yokla, çağrıyı sürüm-toleranslı yap,
   eksik metodu `except AttributeError` ile **FAIL'e çevir** (çökmeye değil).
4. **Fixture içinde CLI modülü import etmek stdout'u GASP EDEBİLİR** (2026-08-09, iki koşum
   sonuçsuz "exit 1" verdi): birçok `scripts/*.py` modül gövdesinde
   `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, …)` yapar (konsol-kodlama koruması).
   Fixture o modülü import/reload ederse sarmalayıcı çöp-toplandığında **alttaki gerçek
   buffer'ı KAPATIR** → testin geri kalanı `ValueError: I/O operation on closed file` +
   `lost sys.stderr` ile ölür ve **hiçbir sonuç satırı basılmaz** (sayaç bile yok).
   `detach()` ile kurtarma denendi, YETMEDİ. Çalışan çözüm: import'tan ÖNCE `sys.stdout`/
   `sys.stderr`i **atılabilir** bir `TextIOWrapper(BytesIO())`e çevir, import bitince yedeği
   geri koy. Bu, *çökme ≠ FAIL*'in harness tarafındaki karşılığıdır: sebep kodda değil
   ölçüm aletindedir.

**FP çapası omurgadır.** "Eksik gate → BLOCKER" yaparken "kayıtlı boş zincir → PASS" çapası
yoksa bilinçli boşluklar da bloklanır; "şu alanı indeksle" derken "mükerrer satır yok"
çapası yoksa tarama sessizce şişer. Mutasyon koşumlarında **geçen vektörler tam da FP
çapalarıysa** tasarım doğrudur — bu, aşırı-sıkılaşmadığının kanıtıdır.

## GERİYE-DÖNÜK DOĞRULAMA (prosedürün kendi kanıtı, 2026-08-01)
mojibake-stdin fix'i → doğru yol KUYRUK+F1-F3'tü (16 hook etkileniyordu; fiilen öyle yapıldı) ·
"paths→globs" önerisi → F4+karşı-kanıtla RED edilirdi (edildi) · include-URI/NameError →
EXPRESS ✓ (dakikalar içinde, güvenle).
