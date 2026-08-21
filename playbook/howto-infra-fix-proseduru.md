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
| **YENİ gate / hook-dalı / validator / paylaşılan araç ÜRETİMİ** (bug değil, kural-onboarding'i — ADR 0019 §5 adım 3) | **infra-expert** (aynı F1-F5 disiplini; lider = tasarım kararı + brifing + diff-review + commit). ⚠ 2026-08-17 dersi: lider "kablolamayı garanti et" baskısıyla hook-dalı + gate + aracı kendisi üretti; ilk sürüm hook'u kırdı — kural-metni "fix"e özgü okunmuştu, ruhu (paylaşılan infra üretimi = infra-expert) buraya açıkça yazıldı |
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

### ⛔ KUYRUĞA GİRİŞ EŞİĞİ (2026-08-22 — kullanıcı kararı, MUST)

> **Kuyruk, fark edilen her şeyin günlüğü DEĞİLDİR; yapılmaya değer işlerin listesidir.**

Bir bulgu kuyruğa **ancak** şunlardan **en az biri** varsa girer:

| # | Şart |
|---|---|
| **(a)** | **Bugün canlı etkisi var** — bir şeyi bozuyor, yanlış sonuç veriyor ya da iş durduruyor |
| **(b)** | **Adı konmuş bir tetiği var** — *"X olursa canlı olur"* diye yazılabiliyor (tetik `deferred-triggers`'a da düşer) |
| **(c)** | **Yayınladığımız bir şey YANLIŞ BİLGİ veriyor** — çıktı/banner/doküman okuyanı yanıltır (sahte-yeşil, sahte-kapsam, eksik ilan) |

**Üçü de yoksa** bulgu **iş kalemi değildir**: dokunduğu dosyaya/changelog'a **not** olarak yazılır ve
orada kalır. *"Kaybolmasın"* diye kuyruğa eklenmez — çünkü kuyruğa eklemek onu **iş** ilan etmektir.

**⭐ NEDEN (ölçüldü, 2026-08-22):** iki ardışık infra turunda kuyruk **8 → 7 → 12** diye BÜYÜDÜ ve
kullanıcı haklı olarak sordu: *"7 madde kapattın 12 madde çıktı, ne zaman bitecek bu?"* Sayımı
yapıldığında son 12 kalemin **12'sinin de yanında "bugün canlı etkisi yok"** yazıyordu ve **5'i
pre-existing**di (bakıldığı için göründüler, o tur üretmedi). Yani liste büyümüyordu — **envanter
görünür oluyordu**, ama ikisi aynı yerde tutulduğu için ayırt edilemiyordu. Eşik uygulandığında
12 kalem **4'e** indi; kalan 8'i not oldu. **Gerçekten önemli olanı, önemsizin arasında saklamak
da bir kayıptır.**

⚠ **İki yan kural:**
1. **Şiddet sayıdan önemlidir.** Turlar arası kıyas *"kaç kalem çıktı"* ile değil, *"çıkanların
   şiddeti düşüyor mu"* ile yapılır. Şiddet düşüyorsa iş yakınsıyordur — sayı yanıltır.
2. **Kısır tur meşrudur.** Her tur yeni bir gate/yetenek eklerse kapı her turda o yeni kodun kenar
   durumlarını çıkarır ve zincir bitmez. Bir noktada **hiçbir şey inşa etmeyen**, yalnız kapatan bir
   tur yapılır; o turun çıktısı ~0 olur ve kuyruk gerçekten kapanır.

## ADIM 3 — İNFRA-EXPERT FIX-SEANSI (kuyruktakiler)

### B0 — HANGİ TESTİ NE ZAMAN KOŞARIZ (2026-08-13)
› **MUST** (infra-expert + lider) · **Denetim:** görünür çıktı satırı + süite-içi
`HARİTA-TAMLIK` vektörü + lider DoD'si — **yeni runtime gate YOK** (ADR 0019 moratoryumu:
mevcut süitenin içinde bir vektör; ihlali zaten çıktıda görünür).
› `prior-art: bulundu` — `governance/infra-test-recipes.md` B0 (core#126) "tam korpus
yalnız SON durumda 1× koşulur" verim notunu zaten taşıyordu; bu blok onun **kimin-ne-zaman**
tarafını netleştirir ve aleti (`--degisen`) ekler. Çoğaltma değil, aynı kaydın devamı.
› ⚠ Bu bir **YER DEĞİŞTİRMEDİR, gevşetme değil**: hiçbir kontrol kaldırılmadı; ara-adım
mükerrerliği indi, sigorta (lider TAM + CI TAM) yerinde. Ayrıntılı analiz: `infra-changelog`
2026-08-13 satırı.
Süite 12 → 113 vektöre büyüdü: **TAM koşum 169,7 sn** (ölçüm 2026-08-13; sayılar bayatlar —
kanonik yer `governance/infra-test-recipes.md` §B0-SEÇİM, burada yalnız gerekçe). Eski pratikte
infra-expert bunu bir seansta 2× koşuyordu; CI de, lider de aynı süiteyi TAM koşuyor ⇒
**aynı sigorta 3-4×**. Yeni iş bölümü:

| Kim | Ne zaman | Komut |
|---|---|---|
| **infra-expert** | ARA adımlar (fix'i şekillendirirken) | `python tests/run_fixture_tests.py --degisen <değişen-dosyalar>` (+ kendi yeni fixture'ını doğrudan koş) |
| **infra-expert** | teslimden önce, kendi worktree'sinde | reçete B0'ın geri kalanı (`run_all_validators` · `compileall` · `core_precommit --all`) |
| **LİDER (DoD, ZORUNLU)** | **merge/PR öncesi 1× TAM** | `python tests/run_fixture_tests.py` — argümansız. Seçili koşum bunun yerine GEÇMEZ |
| **CI** | her PR | değişmedi: `.github/workflows/core-ci.yml` süiteyi TAM koşar |

- `--degisen` **FAIL-CLOSED**'dır: verdiğin dosyalardan biri haritada yoksa TAM süiteye
  düşer ve **bunu satır satır yazar**. "Sessizce 0 birim koştu" hâli yoktur.
- Seçili koşumun çıktısı kendini TAM sanmaz: sonunda `⚠ SEÇİLİ KOŞUM … TAM SÜİTE SONUCU
  DEĞİLDİR` satırı basar. Raporuna bu koşumu **tam süite kanıtı gibi yazma.**
- Ne koşulacağını önce **kuru-koşumla** gör: `--degisen <dosya> --listele`.
- Harita `tests/run_fixture_tests.py` içindeki `HARITA` sabitidir. **Yeni fixture yazınca
  oraya satır ekle** — eklemezsen TAM koşum `HARİTA-TAMLIK/kapsam` vektöründe FAIL verir
  (kendi korpusu: `tests/fixtures/b0_secim/`).
- 📌 İlk gerçek infra işlerinde **çift koşum kıyası** yap (seçili + tam, ikisinin kararını
  yan yana yaz). Kıyas taban veri toplayana kadar geçici bir disiplindir; sapma görülürse
  harita eksiktir → düzelt + kuyruk kaydı aç.

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
   ile EZİP geri almak yerine fixture'a `--mutasyon [--ref <sha>]` bayrağı koy →
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

5. **🔴 D2/5 — MUTASYON TABANI SHA'YA PİNLENİR (DAL ADINA DEĞİL) + korpus tabanı ÖZ-DENETLER**
   › **MUST** (mutasyon koşucusu olan her korpus) · **Denetim:** F3 öz-koşumu + fix-kapanışında
   lider'in bağımsız koşumu — **runtime gate YOK, bilinçli** (ADR 0019 moratoryumu: bu bir
   doküman+korpus *deseni*; ihlali zaten mutasyon çıktısında görünür ve tek çare dokümandır).
   › Kanıt: aşağıdaki ölçülen vaka. (2026-08-10.) Taban olarak **hareketli** bir referans (`origin/main`, `main`,
   `HEAD`, `HEAD~n`) verirsen korpus, fix **merge edildiği gün** ölçmeyi bırakır: taban artık
   *"fix SONRASI"*dır, ayırt edici vektörler PASS'e döner ve komut **hata vermeden** "korpus
   ayırt etmiyor" izlenimi verir. Isırma anı tam da korumanın başlaması gereken andır ve
   çoğu zaman **devir-teslimden sonra** gelir — yani yanlış sonucu senden başkası okur.
   *Ölçülen vaka: bir korpus fix merge edilir edilmez aynı komutta `17/29` yerine `26/29`
   döndü; iki komut yan yana koşulunca fark görüldü.* (Aynı sınıfın `HEAD` varyantı
   2026-08-01'de bir reçetede zaten yakalanmıştı — *"HEAD KULLANMA, commit sonrası HEAD
   fix'tir"*; dal adı onun **daha sinsi** kardeşidir: senin commit'inle değil, **başkasının
   merge'iyle** kayar.)
   - **Varsayılan `--ref` = kusurun CANLI olduğu SHA** (`<kusurlu-sha>`), kodda sabit +
     yanında *neden bu SHA* yazılı. Reçeteye de aynı SHA yazılır.
   - **Öz-denetim ZORUNLU:** korpus, herhangi bir vektörü raporlamadan ÖNCE tabanın gerçekten
     **kusurlu davrandığını** ölçer (kusur "fırlatıyordu" ise: fırlatıyor mu? "sessiz
     geçiyordu" ise: geçiyor mu?). Doğrulayamıyorsa **hiçbir sayı basmaz**; açık
     `[DOĞRULANAMADI]` + **ayrı çıkış kodu** (`2` = alet geçersiz; `1` = vektör düştü, `0` =
     temiz) ile durur. Bu, evin *"doğrulama koşamadı ≠ doğrulandı"* kuralının mutasyon-korpusu
     hâlidir — sayı üretmek, doğrulamış olmak değildir.
   - **Statik/AST çapaları da kaynağı MODÜLLE AYNI YERDEN okur** (mutasyonda
     `git show <ref>:<yol>`, çalışma ağacından DEĞİL): aksi hâlde çapa mutasyonu izlemez ve
     **sahte-PASS** verir — mutasyonda geçen vektör listesi sessizce şişer.
   - ⚠ Bir mutasyon tarifini `<taban-sha>` gibi **yer tutucuyla** bırakmak da aynı ailedendir:
     komut çalıştırılamaz, dolayısıyla **hiç çalıştırılmaz.** Tarifi yazarken SHA'yı bul ve yaz.

**FP çapası omurgadır.** "Eksik gate → BLOCKER" yaparken "kayıtlı boş zincir → PASS" çapası
yoksa bilinçli boşluklar da bloklanır; "şu alanı indeksle" derken "mükerrer satır yok"
çapası yoksa tarama sessizce şişer. Mutasyon koşumlarında **geçen vektörler tam da FP
çapalarıysa** tasarım doğrudur — bu, aşırı-sıkılaşmadığının kanıtıdır.

## GERİYE-DÖNÜK DOĞRULAMA (prosedürün kendi kanıtı, 2026-08-01)
mojibake-stdin fix'i → doğru yol KUYRUK+F1-F3'tü (16 hook etkileniyordu; fiilen öyle yapıldı) ·
"paths→globs" önerisi → F4+karşı-kanıtla RED edilirdi (edildi) · include-URI/NameError →
EXPRESS ✓ (dakikalar içinde, güvenle).
