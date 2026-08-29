# İNFRA TEST-REÇETELERİ — bileşen-başına "dokunmadan önce/sonra koş" adımları

> **Kaynak:** infra-expert arkeoloji-seansı 2026-08-01 (mevcut test-varlıklarından derlendi;
> `[✓]` = o seansta bizzat koşulup doğrulandı). **Kullanım:** infra-expert **F0/F3** bu dosyanın
> ilgili bölümünü okur ve reçeteyi koşar; lider kapanışta bağımsız tekrarlar. Eksik senaryolar
> `governance/infra-findings.md`'de [ÖNERİ] olarak kayıtlı — varmış gibi gösterilmez.

## B0 — ORTAK TABAN (her bileşen için, atlanmaz)
```bash
python scripts/validators/run_all_validators.py     # CORE modu (CI ile aynı)
python -m compileall -q scripts mcp_servers
python scripts/git-hooks/core_precommit.py --all
python tests/run_fixture_tests.py                   # TAM korpus — sayaca değil SATIRLARA bak
python scripts/inspector.py --self-test             # canary    [✓]
```
- ⚠ **`--all` INDEX'i tarar, çalışma ağacını DEĞİL** (`git ls-files` + `git show :<yol>`) →
  **önce `git add`.** Untracked dosya ve unstaged değişiklik hiç görülmez: gate exit 0 der,
  taradığı şey senin yazdığın içerik değildir = **sahte-yeşil.** (Ölçüldü 2026-08-13, 4 vektör:
  untracked→0 · tracked-ama-unstaged→0 · her ikisi `git add` sonrası→1.)
- ⚠ **`--all` CWD-BAĞIMLIDIR — CORE KÖKÜNDEN koş.** Proje kökünden çağrılırsa (junction'lı
  kurulumda tipik: `python core/scripts/git-hooks/core_precommit.py --all`) taradığı ağaç
  **projedir**; projedeki meşru Z-obje adları GENERICIZE-LEAK sanılır ve gate **on binlerce
  sahte ihlalle** exit 1 verir. Bu bir core kusuru DEĞİL, yanlış giriş noktasıdır — ama
  "core bozuk" diye okunur. (Ölçüldü 2026-08-13: proje kökünden `--all` → 25.960 ihlal ·
  core kökünden aynı komut, aynı an → **exit 0**. Ayırt edici: ihlal satırları core'da **var
  olmayan** dosya yollarını gösteriyordu.) Staged-mod (`--all`siz) cwd'den etkilenmez.
- **Verim:** tam korpus yalnız SON durumda **1×** koşulur; ara adımlarda yalnız dokunduğun fixture.
- ⭐ **BÖLÜM 4 — KİP KOŞABİLİRLİĞİ (2026-08-29, kayıt Q210):** TAM süit artık her kipli
  koşucunun **İLK** mutasyon kipini de koşar ve yalnız **"çöktü mü / kipi reddetti mi /
  kurulamadan durdu mu"** sorusunu sorar. Kapsam DAR ve bilinçlidir:
  · **koşucu-başına 1 kip** — tüm 108 kip **+378,5 sn** (süit 283→662 sn, >10 dk tavanı);
    ilk-kip **+78,2 sn** (283→~361 sn). Bugün bulunan 3 çöken kip **2 koşucudan** geliyordu
    ve ikisi de bu daraltmayla yakalanır (kurulum/çağrı kusuru koşucu-başınadır).
  · **ölçüt "düşmeli" DEĞİL** — kimi kip ortama duyarlıdır (ölçüldü: `atc_p1_sonuc
    --mutasyon-stdin`, `PYTHONUTF8` set edilmiş kabukta 22/22, edilmemişte 21/22) ⇒
    "düşmeli" ölçütü süiti operatörün ortamına bağlardı. Korpus GÜCÜ `run_battery`nin işidir.
  · Yeni bir KURAL getirmez (gate değil, kapsam satırı); `--degisen` seçim modunda ATLANIR.
  ⭐⭐ **BÖLÜM 4'ÜN İLK BULGUSU CI ORTAMIYDI — "kip CI'da HİÇ koşmamıştı" sınıfı
  (2026-08-29 ileri-fix, PR #181 kırmızısı, run 33265820879):** yerel süit **208/208 yeşil**
  iken CI BÖLÜM 4'te **28/34** verdi. Düşen 6 koşucunun tamamı `KURULAMADI(rc=2)` idi ve
  kök **ürün kodunda değil ORTAMDA**ydı: `actions/checkout@v5` parametresiz = **sığ klon**
  (`fetch-depth 1`) ⇒ mutasyon tabanını **pinli SHA**'dan alan koşucular (`git show
  <sha>:<yol>`) blob'u bulamıyordu. Yani kip korpusunun **%17,6'sı (6/34) CI'da hiç
  koşmamıştı**; BÖLÜM 4 olmasa bu görünmezdi. Çözüm: `core-ci.yml` → `fetch-depth: 0`
  (maliyet size-pack **6,93 MiB / 233 commit**; emsal `project-guard.yml`). Sonra derin
  ağaçta **34/34**.
  🔁 **CI İKİZİNİ YERELDE KUR (bu sınıfta İLK komut, tahmin etme):**
  `git clone --depth 1 --branch <dal> file:///<repo-yolu> <tmp>` → doğrula:
  `git -C <tmp> rev-list --count HEAD` = **1** ve `git -C <tmp> cat-file -e <pinli-sha>`
  = **hata**. Sonra `env -u PYTHONUTF8` ile koş. Bu ikiz PR #181 kırmızısını **birebir**
  (28/34, aynı 6 koşucu) yeniden üretti.
  ⛔ **BOŞ SEBEP = AYRI BİR KUSUR, ORTAM DEĞİL:** o 6 FAIL'in **2'si** hiçbir sebep
  yazmıyordu. Kök: `yukle()` `sap_client` import-anı için `sys.stdout/stderr`'i BytesIO ile
  sarmalar, `git_show()` o pencerenin İÇİNDEN çağrılır ⇒ `print()` ile basılan teşhis
  **atılan tampona** gider (`sys.exit(2)` sonrası dışarıya 0 bayt). Ev deseni: teşhis akışı
  swap'tan ÖNCE `_GERCEK_ERR = sys.stderr` diye yakalanır, `print(..., file=_GERCEK_ERR)`.
  **F1 kapsamı ölçüldü:** swap YAPAN 10 koşucudan `exit 2/3` ile de duran **3'ü** riskli;
  `run_battery` fixture'ının exit'leri swap penceresi DIŞINDA ⇒ etkilenen **tam 2 koşucu**.
  ⚠ **Mutasyon çapası "boş değil" OLAMAZ:** süit tarafına eklenen yer-tutucu
  (`<KOŞUCU HİÇ ÇIKTI ÜRETMEDİ …>`) koşucu katmanının mutasyonunu MASKELER. Çapa
  **gerçek metin** olmalı (`git show <sha>:… → fatal`). Negatif kontrol git'siz/ortamsız
  koşar: `--mutasyon --ref 0000000deadbeef` → sebep **218/217 karakter**, exit 2;
  `file=_GERCEK_ERR` sökülürse aynı komut **0 karakter**.

### B0-SEÇİM — `--degisen` (ara adımlar; 2026-08-13)
> Ölçüldü: TAM koşum **169,7 sn / 113 vektör**. Tek-validator değişikliği için seçili
> koşum **0,4 sn**; `claude_overlay` **4,6 sn**; `pre_tool_guard` **32,4 sn** (55-payload
> korpusu dâhil). Kimin-ne-zaman koştuğu: `playbook/howto-infra-fix-proseduru.md` ADIM-3 B0.
```bash
python tests/run_fixture_tests.py --degisen <dosya> [<dosya> ...] --listele   # kuru koşum
python tests/run_fixture_tests.py --degisen scripts/hooks/pre_tool_guard.py   # seçili koşum
python tests/run_fixture_tests.py                                            # TAM (lider/CI)
```
- Harita = `tests/run_fixture_tests.py::HARITA` (**açık sabit**; docstring'lerden üretilmez).
  Yeni fixture yazınca satır ekle — eklemezsen TAM koşum `HARİTA-TAMLIK/kapsam` FAIL verir.
- **FAIL-CLOSED negatif-testi** (fail-open'a kaymadığını böyle ölçersin):
  ```bash
  python tests/run_fixture_tests.py --degisen scripts/hic_yok.py --listele
  # beklenen: "bilinmeyen dosya … → TAM süite" + "⇒ KARAR: TAM süite koşulacak (fail-closed)"
  python tests/run_fixture_tests.py --degisen --listele        # boş liste → aynı karar
  ```
  ⚠ `exit 0` burada da tek başına kanıt değildir — **KARAR satırını oku** (seçili koşum
  sonunda `⚠ SEÇİLİ KOŞUM … TAM SÜİTE SONUCU DEĞİLDİR` yazar; o satır varken "süite yeşil"
  denmez).
- Korpus: `python tests/fixtures/b0_secim/run.py` → **20/20**. İki mutasyon (ikisi de
  koşulur, biri diğerini kapsamaz):
  · `--mutasyon-failopen` (bilinmeyen dosya → sessiz daraltma) → **15/18**; düşen: N1 · N1b · N5.
  · `--mutasyon-tamlik` (harita-tamlık kontrolü sökülü) → **16/18**; düşen: N2 · N3.
  **FP çapaları her iki mutasyonda da AYAKTA** (P1-P5 · N6 açık-boş bildirim · F1 argümansız
  davranış · F2 sahte-alarm yok · F4 doküman dalı) ⇒ seçim aşırı-sıkılaşmadı. *(Mutasyon `git show <sha>` ile DEĞİL,
  fixture içi enjeksiyonla yapılır: kod taban SHA'da hiç yoktu — hedef geçmiş bir commit değil,
  reddedilen tasarım kararı.)*

### B0-BATARYA — `run_battery.py` (ara adımların TEK komutu; 2026-08-29)
> **Ölçüldü (30 günlük ajan-transkript denetimi):** bir infra koşusunda batarya
> (taban koşumu · her mutasyon kipi · kardeş fixture · `core_precommit --all`) medyan
> **8 kez** tekrarlanıyor ve her batarya **4-6 ayrı kabuk turu** yiyordu. `run_battery`
> bunu **tek tura** indirir; ham çıktı `.tmp/battery/`e yazılır, ekrana ≤25 satır özet çıkar.
```bash
python tests/run_battery.py <fixture-adi>                       # taban + TÜM mutasyon kipleri
python tests/run_battery.py <fixture> --kardes <ad> [<ad> …]    # + komşu regresyon (yalnız TABAN)
python tests/run_battery.py <fixture> --kardes <ad> --kardes-tam # kardeşin kipleri de koşsun
python tests/run_battery.py <fixture> --precommit                # + core_precommit --all
python tests/run_battery.py <fixture> --liste                    # yalnız keşif (hiçbir şey koşulmaz)
```
**DÜZEN (kadans):** her **Edit paketinden sonra** `run_battery <dokunduğun fixture>` ·
`--degisen` seçili süiti komşu korpuslar için · **tam süit (`run_fixture_tests.py`) yalnız
koşunun SONUNDA 1×** (ara adımlarda değil; CI zaten TAM koşar). ⛔ **Batarya tam süitin
yerine GEÇMEZ ve F3'ü GEVŞETMEZ:** üç-bağlam şartı (bilinen-bozuk→FAIL · bilinen-temiz→PASS ·
görev-DIŞI üçüncü bağlam) aynen durur — batarya onları *koşan* araçtır, *azaltan* değil.
- **Kip keşfi üç katmanlı** (`--help`e güvenmez): ① kaynaktaki kip-kümesi literali (ad-bağımsız;
  ⚠ **kıyas operandı beyan sayılmaz** — `set(k) == {"--mutasyon-x"}` başka koşucuyu TARİF eder)
  ② docstring-dışı string sabitleri (yorumlar AST'te yoktur ⇒ `--mutasyon-ZIRVA` örnekleri
  kendiliğinden elenir) ③ **modül docstring'i — bu katman ŞART**: üç koşucu
  (`atc_p1_sonuc` · `fs_docstd` · `post_tool_failure_bash`) kipleri `startswith` + son-ek ile
  çözer, geçerli liste yalnız docstring'dedir. Katman-3 sökülürse **16 kip sessizce** kapsam
  dışı kalır. Ölçüldü (2026-08-29): 90 koşucunun 33'ünde kip var, **33/33 çözülüyor, 0 hayalet**.
- **`exit 0` tek başına anlam taşımaz** — satır etiketleri AYRI: `DUSTU` (exit≠0) ·
  `AYIRDI` (exit 0 + skor tabandan farklı = kendi öz-testini koşan koşucu) · `KACTI` (exit 0 +
  AYNI skor) · `OLCULEMEDI` (skor okunamadı) · `KURULAMADI` (**exit 2 VEYA 3**) · `KIP-RED`
  (`[DURDU]`/`[KULLANIM]`) · `COKTU` (Traceback). ⛔ *"Mutasyon exit≠0 vermeli"* kuralı **YANLIŞ
  olurdu**: canlı korpusta 33 kipin **15'i exit 0** döner (ölçüldü) ⇒ naif kural %45 sahte-FAIL üretirdi.
- Ölçülen tek-komut maliyeti (2026-08-29, bu makine): `infra_write_guard` **8 birim / 26,6 s** ·
  `run_battery` **7 birim / 30,1 s** · `b0_secim` **3 birim / 6,9 s**.
- Korpus: `python tests/fixtures/run_battery/run.py` → **25/25**; 7 mutasyon, her biri TEK çapa
  keser: `--mutasyon-kacak-kor`→N2 · `--mutasyon-kurulum-kor`→N4b+N4c · `--mutasyon-red-kor`→N4 ·
  `--mutasyon-cokme-kor`→N5 · `--mutasyon-olcum-kor`→N8 · `--mutasyon-kesif-kor`→P2+P10 ·
  `--mutasyon-uc-kor`→**N4c** (exit-3 kapsamı sökülür).
- ⭐ **exit 3 = KURULAMADI (2026-08-29, kayıt Q210 — aracın KENDİ sahte-yeşili):** araç
  başlangıçta yalnız exit 2'yi "kurulamadı" sayıyordu; oysa DÖRT koşucu çapası tutmayınca
  `sys.exit(3)` döner (`fm_imza_doc_sync` · `infra_write_guard` · `std_tablo_include_kapsami` ·
  `reviewer_skip_sozlesmesi`). Sonuç: **çapası bayatlamış bir mutasyon `DUSTU(rc=3)` diye
  YEŞİL raporlanıyordu** — bu tur canlı yaşandı (3 bozuk mutasyon PASS geçti). Genişleme
  korpustan ölçüldü: 108 kip taramasında DÜŞEN her mutasyon rc=1 verir, hiçbiri 3 vermez ⇒
  `DUSTU`dan hiçbir gerçek vaka çalınmaz (saf precision düzeltmesi).
- ⚠ **Çocuk ortamına `PYTHONUTF8` ENJEKTE EDİLMEZ** (bilinçli): enjekte edilseydi burada
  yeşil olan koşucu CI'da (env'siz) kırmızı olabilirdi — *lokal yeşil ≠ CI yeşil* sınıfı.
- ⚠ Batarya **bir kapı değildir**: hiçbir kuralı zorlamaz, `run_all_validators`/pre-commit
  yerine geçmez. Çıktısının son satırı bunu her koşumda yazar.

## B0b — NEGATİF TEST HARNESS'I (hook'a sentetik payload verirken)
> Geçerlidir: `pre_tool_guard` · `pull_before_edit` · stdin'den JSON okuyan HER hook.
- ⛔ **`exit 0` "serbest" DEMEK DEĞİLDİR.** Hook'lar bozuk/yabancı girdide de **0** döner
  (`json.load` → `except: return 0`, bilinçli fail-safe). Yani *"guard bu payload'ı geçirdi"*
  ile *"guard payload'ı hiç okuyamadı"* AYNI çıktıyı verir. 0 gördüğünde **önce payload'ın
  PARSE edildiğini kanıtla** — stderr'de blok mesajı yoksa ölçümün geçersiz olabilir.
- ✅ **KÖK-FIX 2026-08-13 — artık AYIRT EDİLEBİLİR (`exit 0` DURUYOR).** Girdiye dayalı karar
  veren **14 hook** parse-fail dalında stderr'e `GIRDI-PARSE-EDILEMEDI` notu basar (hook adı +
  "KARAR DEGILDIR" + bu reçeteye atıf). **Ölçüm kuralı:** `0` gördüğünde stderr'e bak —
  **not VARSA ölçümün GEÇERSİZ** (payload hiç okunmadı), **not YOKSA gerçekten meşru serbest.**
  Exit davranışı bilerek değişmedi; `2` hâlâ tek blok sinyalidir (not blok imzası SAYILMAZ).
  Not **stderr**'e gider (stdout JSON sözleşmesi kirlenmez) ve **ASCII**'dir (cp1252 tuzağı).
  **Kapsam dışı 2 hook** (`pre_compact`, `tooling_radar_check`): stdin yalnız boşaltılır,
  karara girmez → not basmaz; korpusun **iç kontrol grubudur.**
- **Kök tuzak: elle yazılan `\\` kabuğa TEK `\` olarak ulaşır** → JSON'da geçersiz escape
  (`Invalid \escape`) → parse-fail → 0. Ölçüldü 2026-08-13 (aynı payload, tek fark yol biçimi):
  `\\`→**0** · `/`→**2 BLOK** · `\\\\`→**2** · byte-tam `\\` dosyadan→**2**.
- ✅ **Güvenli yollar:** yolları **`/` ile yaz** (Windows'ta `Path` çözer) · VEYA payload'ı
  **program üretsin** (`json.dumps` → dosya) ve `< payload.json` ile ver.
- ✅ **Pozitif kontrol ZORUNLU (PATTERN #19):** aynı harness'ta **bloklaması bilinen** bir
  payload koş; o da 0 dönüyorsa ölçtüğün şey guard değil, harness'ındır.
- 🔴 **BORU HARNESS'I ORTAM-BAĞIMLIDIR — hiçbirine güvenme (2026-08-13, İKİ ZIT ÖLÇÜM):**
  aynı worktree/aynı makine, farklı süreç-zinciri → bir koşumda PS borusu **exit 2**
  (3 payload) ve kabuk borusu **2**; diğer koşumda PS borusu **0**, kabuk borusu **255**
  (taşıyıcı hiç koşmamış: `cat` yok). ⇒ "PS pipe bozuk" da "PS pipe sağlam" da
  GENELLENEMEZ. Tek güvenilir yol: **payload'ı dosyaya yaz + `<` ile ver + pozitif kontrol.**
  `printf`e geçmek de kurtarmaz — kabuk kadar **payload'daki backslash** da belirleyicidir;
  suçlamadan önce payload'ı `od -c`/`cat -A` ile GÖR ve taşıyıcının KOŞTUĞUNU doğrula
  (255 / "command not found" = guard sonucu DEĞİL).
- Korpus: `python tests/fixtures/negatif_test_harness/run.py` → **15/15**. **İKİ MUTASYON, ikisi de
  koşulur** (biri diğerini KAPSAMAZ — biri exit'i, diğeri notu çivilliyor):
  · `--mutasyon` (EXIT değişmezi: stdin fail-safe `return 0`→`return 2`) → **10/15**; düşen 5:
    V5 · V8 · V9 · V10 · V13. *(Kapsamı `return 0` çapası olan 10 hook; `data = {}` ile devam
    eden 4 hook bu mutasyonun DIŞINDADIR — onları `--mutasyon-notsuz` ölçer.)*
  · `--mutasyon-notsuz` (NOT değişmezi = **fix'in sökümü**) → **9/15**; düşen 6:
    V6 · V7 · V8 · V9 · V13 · V15.
  **FP çapaları HER İKİ mutasyonda da AYAKTA** (V1/V2 blok · **V3 meşru-serbest hâlâ SESSİZ** ·
  V4 pozitif kontrol · V14 stdout · V16 kayıt) ⇒ "doğru vaka bozulmadı" kanıtı korunuyor.
  ⚠ Korpus taşıyıcı exit'lerini BASAR ama EŞİTLİĞİNİ assert ETMEZ (ortam-bağımlı); sözleşme
  yalnız **referans taşıyıcıda** (doğrudan stdin) ölçülür: *imza VAR ⇔ exit 2*.

## B1 — hook_shim (proje-tarafında yaşar!)
- Konum-uyarısı: shim DEV_CORE'da YOK — `<proje>/scripts/hook_shim.py`; test proje-kökünden.
- Mojibake-regresyonu: `printf '%s' '{"prompt":"GÖREV: şu ekrana kolon ekleyelim"}' | python scripts/hook_shim.py intake_triage` → çıktıda `GÖREV` doğru (GA–REV = stdin-reconfigure geriledi).
- Fail-closed değişmezi: junction-kopukken bloklayıcı hook → **exit 2** (1 değil).
- **`printf` kullan, `echo` KULLANMA** — echo backslash bozar → JSON-fail → fail-safe-0 → "geçti" sanılır (5d6b90d'nin yaşadığı tuzak).
  ⚠ **`printf` TEK BAŞINA YETMEZ** (ölçüldü 2026-08-13): elle yazılan `\\` kabuğa zaten tek `\` olarak ulaşır → printf onu sadakatle basar → yine parse-fail/0. Belirleyici olan kabuk değil **payload'daki backslash** — bkz. **B0b**.

## B2 — pre_tool_guard
- Pozitif-kontrol (guard yaşıyor mu; PATTERN#19): hedefsiz `gh pr create` payload'ı → **exit 2** `[✓]`; `gh pr list --repo ...` → exit 0 `[✓]`.
- Konformans META-GATE: `python scripts/tests/guard_conformance.py --self-test-only` `[✓ Z4-öz-test]` + `--project ../template_project`.
- Yüzey: `python scripts/tests/test_pre_tool_guard.py`; canlı-eksen `IX_GUARD_TEST_LIVE=1` (atlanırsa ADIYLA yazdırılır).
- Kablolama≠kod: doğrudan-çağrı kablolamayı ölçmez → `ix_doctor` layer-4 matcher kontrolü.
- Kaldırılmış-kural iddiası öncesi `removed-controls.md` oku (R9/R10 YOK; donmuş-köke Write→exit 0 BEKLENİR).

## B3 — session_start + behavior_manifest + config_change_guard
- `python scripts/behavior_manifest.py` (verify) → temizde sessiz/OK.
- İmza 6'lısı: yorum→AYNI · CRLF→AYNI · hook-sil→**FARKLI** · matcher→**FARKLI** · bozuk-JSON→"?" · sıra→AYNI (ilk-üçü ters = FP geri; 3-4 AYNI = kapsam-kaybı).
- config_change_guard: davranış-dosyası sentetik-değişiklik → exit 2 + config-changes.log satırı.
- 4 junction TEK TEK raporlanmalı (toplu-OK tek kırığı gizler).
- **`source` DALI (2026-08-29).** SessionStart girdisindeki `source` (`startup|resume|clear|compact|fork`) gövdeyi ikiye ayırır.
  ⚠ **Ölçüm kuralı: çıktıyı HAM stdout'ta ARAMA** — hook `json.dumps` varsayılanıyla basar (`ensure_ascii=True`) ⇒ Türkçe harfler `\uXXXX` olarak durur; çapayı JSON'dan ÇÖZ (`hookSpecificOutput.additionalContext`), yoksa **sahte-KIRMIZI** alırsın.
  · `source="compact"` → oturum-başı TALEBİ (*"Yeni oturumun ILK yaniti …"*) **YOK** + `[DURUM CAPASI …]` **VAR** (dal · son commit · `git status` özeti).
  · `source="startup"` / alan **YOK** / **tanınmayan** değer / **bozuk girdi** → bugünkü çıktı **BAYT-EŞ** (fail-safe yön = mevcut davranış). `resume`/`clear`/`fork` bu turda **DEĞİŞMEDİ**.
  ⛔ **ÇAPA TERİM DEĞİL, TALEP:** `"Ekran Teyidi"` dizesi compact gövdesinde de geçer (*"… ISTENMIYOR"*) ⇒ o dizeye dayanan assertion **ayırt edici DEĞİLDİR** (ilk koşumda ölçüldü: 3 vektör sahte-KIRMIZI). Çapa: `"Yeni oturumun ILK yaniti"`.
  ⛔ **Çapa GİT'ten türetilir, `.claude/active_package`'tan DEĞİL** — state dosyası sessizce bayatlar (ölçülmüş vaka: state bir paketi, fiilen çalışılan iş BAŞKA bir paketi gösterdi; `pre_compact` yanlış SESSION_NOTES'a yönlendirdi). State'e yaslanan çapa o drift'i compact SONRASINA taşır. **Ayırt edici test:** git dalını değiştir, state dosyasına DOKUNMA → çapa değişmeli (V8).
  · **3. BAĞLAM:** git'siz kök · commit'siz repo → çapa **sessizce düşer**, exit **0**, gövde sağlam (hook birden çok projede koşar; çöken çapa çapanın kendisinden pahalıdır).
  · Sağlık kontrolleri compact dalında da **KOŞAR** (bilinçli karar: temizken zaten sessizdirler ⇒ maliyet ödenmiyor; compact oturumun ORTASINDADIR ve junction/damga/manifest sinyali tam o aralıkta değişir).
  ⛔⛔ **V3'ÜN TABANI GİT'TEN ALINMAZ (2026-08-29, 2. tur — CI kırmızısının kökü).** İlk yazımda
  taban `git show HEAD:scripts/hooks/session_start.py` idi ⇒ fixture **yalnız fix commit'lenmeden
  ÖNCE** geçebiliyordu; commit atılınca taban = fix ⇒ `OLCULEMEDI` (PR #179, run 33258089818).
  **SHA'ya pinlemek de çözüm DEĞİL:** CI `actions/checkout@v5` **sığ klon** yapar (`fetch-depth 1`)
  ⇒ `git show <eski-SHA>:…` blob'u bulamaz (`git clone --depth 1` ile taklit edilip ölçüldü).
  📌 **GÜNCELLEME 2026-08-29 (Q210 ileri-fix) — ORTAM DEĞİŞTİ, KARAR DEĞİŞMEDİ:** `core-ci.yml`
  artık `fetch-depth: 0` kullanıyor ⇒ *sığ klon* gerekçesi core-ci için **artık geçerli değil**
  (pinli, main'den erişilebilir SHA'lar CI'da çözülür). ⛔ Bu, V3'ün tasarımını **geri açmaz**:
  V3'ün tabanı `git show`'dan **zaman bağımlılığı** yüzünden çıkarılmıştı (fix merge edilince
  taban = fix) ve bunu hiçbir checkout ayarı düzeltmez. Sığ-klon yalnızca **ikinci** ve bağımsız
  gerekçeydi. V3 bugünkü hâliyle (kaynaktan türetme) kalır; `git show HEAD:` hâlâ YASAK.
  **Dondurulmuş kopya da REDDEDİLDİ:** tüm dosyayı dondurur ⇒ startup gövdesindeki ilerideki HER
  meşru edit V3'ü kırar, vektör kronik-kırmızıya döner. **Kabul edilen yol** (`fa1adfe`/PR #177
  reçetesinin aynısı): taban BUGÜNKÜ kaynaktan **tek dal satırı** sökülerek türetilir
  (`_taban_kaynak()`; `_DAL_SATIRI` sabiti `--mutasyon-dalsiz` ile ORTAK ⇒ ayrı ayrı bayatlayamaz).
  **İki kurulum çapası, ikisi de `exit 2` + SAYI YOK:** dal satırı 1 kez bulunmazsa `TABAN
  URETILEMEDI` · türetilen taban `compact` girdisinde hâlâ fix gibi davranırsa `TABAN KOZMETIK`
  (trivial-yeşil koruması). Doğrulaması: N1 satırın YAZIMINI değiştir · N2 türetmeyi NO-OP yap.
  **Bir kereye mahsus çapraz kontrol (derin klon):** türetilen taban ↔ gerçek `1746040` blob'u
  → `startup` ve `compact` çıktıları **BAYT-EŞ** (1747 B). ⚠ CI'da bu kontrol YAPILAMAZ (sığ klon);
  fixture git'e HİÇ bağlı değildir, yalnız kendi sahte deposunu kurar.
  Korpus: `python tests/fixtures/session_start_compact_dali/run.py` → **22/22**. **ÜÇ mutasyon** (hiçbiri diğerini kapsamaz): `--mutasyon-dalsiz` → **15/22** (düşen V1·V1b·V2·V8·V8b·V9·V10) · `--mutasyon-capasiz` → **19/22** (V2·V8·V8b) · `--mutasyon-state` → **19/22** (V2·**V7**·V8). FP çapaları (V3 bayt-eşlik · V4/V4b · V5/V6/V6b fail-safe · V11 · V12 · V13 · V14) ÜÇ mutasyonda da **AYAKTA**.

## B4 — pull_before_edit
- Bayat-seans SAP-source Edit-payload → **exit 2** ve mesajdaki komut **`core/scripts/sap_sync_pull.py`** (proje-göreli).
- Taze-seans → 0; SAP-dışı → 0; damga **proje-kökü** `.claude` altında (DEV_CORE'a yazıyorsa d2d326d regresyonu).
- `IX_SOURCE_ROOT` farklı-adla hâlâ yakalıyor (4 fixture).
- **DAMGA EŞZAMANLILIĞI (2026-08-28, E-02):** `python tests/fixtures/damga_yarisi/run.py`
  → **14/14 + 6 mutasyon**, exit 0 (~42 sn; süreç başlatır, en yavaş vektör budur).
  Değişmezler: `_stamp` OKUMA+YAZMA'yı **tek kilidin içinde** yapar (yalnız yazımı kilitlemek
  kayıp-güncellemeyi ÇÖZMEZ — M2 sınır mutasyonu tam bunu sınar) · yazım `os.replace` ile
  **atomik** · kilit alınamazsa **görünür uyarı** (M4: sessizce yutulursa korpus kırmızı) ·
  **bayat** kilit kırılır (M3: kırılmazsa araç kalıcı kilitlenir) · Windows'ta kilit
  `PermissionError` de verir, bu **meşguldür**, çökme değil (M6).
  ⭐ D1 vektörü yarışa DEĞİL `_now_iso` seam'ine dayanır → deterministtir; yük vektörü
  (8×12) yalnız istatistiksel destektir, **tek kanıt sayılmaz**.
  ⛔ 3. bağlam (`pull_before_edit._is_fresh`) SİLİNMEZ: yazıcı ile okuyucu **ayrı modüldür**,
  biri değişirse eksen sessizce boşalır (HARİTA'da o dosya da bu korpusa bağlıdır).

## B5 — skill_injector / worktype_hint / ITG-katmanları
- ITG A/B/C: regex-tetik→marker, backstop-sessiz · keyword-dışı-talep→ilk SAP-tool'da backstop-enjekte · ping/Bash→sessiz.
- Diyakritik: "gelistir" TETİKLER; "istersen"/"isteğe bağlı" TETİKLEMEZ.
- task-notification payload'ı → sessiz. worktype: tip-başına 1 enjeksiyon (struct/tablo AYNI grup!).
- Sınıf-kuralı: keşif ekleyeceksen NATIVE-description'a, hook-regex'ine DEĞİL.
- ⭐ **MODÜL-İPUCU REGEX'İ ↔ METODOLOJİ SÖZLÜĞÜ (2026-08-21) — `_MODULES`'a dokunmadan önce:**
  ```bash
  python tests/fixtures/intake_modul_carpismasi/run.py                     # 19/19
  python tests/fixtures/intake_modul_carpismasi/run.py --mutasyon-pp-geri   # 14/19
  python tests/fixtures/intake_modul_carpismasi/run.py --mutasyon-qm-geri   # 16/19
  python tests/fixtures/intake_modul_carpismasi/run.py --mutasyon-asiri-dar # 11/19
  ```
  - ⛔ **Tek-kelimelik SAP terimi bu evin sözlüğüyle çakışabilir.** `reçete` = playbook tarifi,
    `kusur` = defect. İkisi de PP/QM kancasıydı ve infra turlarında yanlış ipucu veriyordu.
  - ⛔⛔ **DARALTMA = POZİTİF KONTROL BORCU.** *"Artık ateşlemiyor"* TEK BAŞINA yetmez;
    *"gerçek PP/QM talebini HÂLÂ yakalıyor"* da gösterilmelidir. Çapalar **B1-B8** ve
    **SİLİNEMEZ**; `--mutasyon-asiri-dar` sekizini birden düşürür. 19/19 verirse korpus boştur.
  - ⛔ **Ölçüm DOSYA-GREP'İ DEĞİL, GERÇEK KULLANICI PROMPT KORPUSUDUR** — hook
    `UserPromptSubmit`e bağlıdır. Transcript'lerden `type=="user"` mesajları çıkarılır
    (`utils.claude_paths.transcript_dizini`), eski↔yeni regex AYNI korpusta yan yana koşulur.
    Dosya-grep'i yalnız bir göstergedir.
  - ⚠ **FP vektörünü GERÇEK BİÇİMDE yaz:** eski `\breçete` diyakritik-bağımlıydı ⇒ ASCII
    "recete" içeren bir FP vektörü fix-ÖNCESİ de ateşlemez = **TRIVIAL YEŞİL** (ilk taslakta
    tam bu oldu; mutasyon altında yine PASS verdi).
  - ⚠ **Mutasyon yer-tutucusu `r"|"` OLAMAZ** — boş alternatif regex'i HER ŞEYE eşletir;
    "aşırı-dar" sanılan mutasyon "aşırı-geniş" olur ve ölçüm tersine döner.
  - ⛔ Kapsam dışı (ayrı karar): tetiğin kendisi (*"infra turu geliştirme talebi sayılıyor"*)
    ve skill'in `DO NOT USE FOR` listesi — **İPTAL değil, ERTELENDİ**.
  - ⓘ **Ölçülmüş ama DOKUNULMAMIŞ komşu FP'ler** (aynı sınıf, ayrı karar): PP'de kalan 90
    ateşin **62'si `\bBOM\b`** (= Byte Order Mark, evin PowerShell-BOM tuzağı), 18'i
    `yönlendirme`, 8'i `routing`; QM'de kalan 6'nın 4'ü `kalite kontrol` (= belge kalite
    kontrolü). `BOM` tek başına `reçete`den (51) DAHA BÜYÜK bir FP kaynağıdır.

## B6 — post_validate
- HIZLI_KUME 5 sınıf → hızlı-tur; **tablo-DIŞI → TAM tur** (hızlıya düşerse fail-open'a kaydı).
- Türkçe alt-validator çıktısı relay'de bozulmamalı (capture encoding).

## B7 — recall_inject + build_recall_index
- P: "classrun derdi" → PATTERN#19 · RAP-sorgusu → 3-ders · "validator/hook" → infra-howto ilk-sıra.
- N: kısa-prompt sessiz · bozuk-indeks exit-0 (fail-open) · alakasız sessiz.
- `recall_inject` için fixture bilinçli YOK (deterministik-LLM'siz) → reçete = sentetik-payload
  (howto-sistem-denetimi §3). **`build_recall_index` için ARTIK FİXTURE VAR** (aşağı bkz.).
- ⭐ **MEMORY.md AYRIŞTIRMA SÖZLEŞMESİ (2026-08-21) — bu dosyaya dokunmadan önce oku:**
  ```bash
  python tests/fixtures/recall_index_ozetsiz/run.py                      # 16/16
  python tests/fixtures/recall_index_ozetsiz/run.py --mutasyon-geridusus-yok  #  8/16
  python tests/fixtures/recall_index_ozetsiz/run.py --mutasyon-dar-desen      # 11/16
  python tests/fixtures/recall_index_ozetsiz/run.py --mutasyon-uydur          # 12/16
  python tests/fixtures/recall_index_ozetsiz/run.py --mutasyon-satirasan      # 12/16
  ```
  - ⛔ **Ayraç deseni `\s*` OLAMAZ** — `\s` satır sonunu kapsar ve özetsiz bir satır bir
    SONRAKİ satırın metnini `oz` diye yutar (kayıt VAR ama özeti BAŞKA DERSE ait).
    Canlı `MEMORY.md`'de mevcut 90 kaydın **42'si** böyleydi. Doğrusu `[ \t]*`. Çapa: **C6**,
    yalnız `--mutasyon-satirasan` altında düşer.
  - ⛔ **Kaynak yoksa UYDURMA yok**: frontmatter yok / `description:` yok / dosya diskte yok
    → **kayıt da yok**. Çapalar **N1/N2/N3**; `--mutasyon-uydur` bunları sınar.
  - ⛔ **Kapsam `^- \[` DEĞİLDİR**: canlı indekste en değerli dersler `- ⭐ [...]` / `- ⛔ [...]`
    biçimindedir ve dar desen onları GÖRMEZ; bir satırda birden çok link olabilir. Çapalar
    **P2/P3/P5**; `--mutasyon-dar-desen` bunları sınar.
  - ⛔ **`anahtar` formülü (`baslik×3 + oz`) DEĞİŞMEZ** — kapsam açılır, skorlama açılmaz (**C3**).
  - Ölçüm hermetiktir: `CLAUDE_CONFIG_DIR` ile `~/.claude` yönlendirilir ve **gerçek CLI**
    koşulur (kod ≠ kablolama). Kanonik sayılar: `governance/infra-changelog.md` (bu bölümde
    tekrarlanmaz — iki yerde yaşayan rakam bayatlar).
  - ⛔ Mutant **derlenmiyorsa** koşucu **exit 2 / DOGRULANAMADI** verir: *"KURULAMADI ≠ KAÇTI"*.

## B8 — watchdog / pre_compact / post_tool_failure / instructions_log / radar_check
- **watchdog_launch brifing eksenleri (2026-08-19):** `[PRIOR-ART / KB-01]` ateşleme ölçütü **metin değil arama**: brifingde adı geçen + `scripts/`te var olan script, `playbook/`de ≤2 dosyada geçiyor ve o dosyalar brifingde ANILMIYOR. ⛔ *"atıf var mı"* diye ölçme — gerçek korpusta brifinglerin **%98,6'sı** zaten yol atfı taşır (trivial yeşil). Gürültü tabanı: **%13,9** ateşleme / 570 brifing, medyan 1 ms. FP çapası şart: reçete zaten anılmış · var-olmayan script adı · >2 reçetede geçen genel araç · <400 karakter. Fail-open yasağı iki çapa ister (dizin-yok + bozuk-payload → `KOSMADI`). Notlar **4 emit yolunun hepsinde** çıkmalı (daemon/bash bulunamasa bile). Korpus: `prior_art_kb01`.
- ⛔⛔ **D2 KURATLI KANCALAR (`T3-KİMLİK` + `DEPLOY`) — EKLENDİ ve AYNI GÜN GERİ ALINDI
  (2026-08-21). Bu blok artık bir REÇETE DEĞİL, bir KALDIRMA KAYDIDIR.**
  `tests/fixtures/brifing_lint_d2/` **YOKTUR** (kaldırıldı) — buradaki eski koşum satırları
  (`18/18` · `--mutasyon-kimlik` · `--mutasyon-deploy` · `--mutasyon-fren`) **koşulmaz**.
  Kanonik gerekçe: **`governance/removed-controls.md`** + `infra-changelog.md`
  *2026-08-21 (akşam)* satırı. Burada yalnız **`_brifing_lint`'e eksen eklemeden önce**
  okunması gereken ders durur:
  - ⛔⛔ **ATEŞLEME ORANI TEK BAŞINA KABUL ÖLÇÜTÜ DEĞİLDİR.** Bu iki kanca *"%4,8 + %5,3 =
    bant altı ✅"* diye kabul edildi ve **precision 0** ile merge edildi: 609 gerçek brifte
    `T3-KİMLİK` 30 ateşlemenin **30'u salt-okur**, `DEPLOY` 32 ateşlemenin **0'ı** gerçek
    deploy işi. Ateşlenen *oran* doğruydu, **ateşlediği şey** değil.
  - ⭐ **YENİ KABUL ÖLÇÜTÜ — ÜÇÜ BİRDEN:** ateşleme **<%13,9** (ev bandı gürültü tabanı)
    **VE** precision **≥%70** **VE** recall **≥%50**. Aleti hazır:
    `governance/research/brifing-lint-olcum-2026-08-21/precision_harness.py`
    (yer-gerçeğini brifin METNİNDEN değil **rol + açık beyandan** türetir; tartışmalı
    vakaları `AMBIVALENT` kovasına alıp paydadan çıkarır — ölçüm kendi lehine oynamaz).
  - ⛔ **BASTIRICI DESEN, HEDEFLE TERS KORELASYONLU OLABİLİR — asıl ders bu.** `fren`
    deseni çıplak `DOKUNMA` içeriyordu; o kelime **gerçek yazma briflerinin** kapsam-sınırı
    cümlesidir (*"başka dosyaya dokunma"*) ⇒ tam da hedef sınıfı susturuyordu. Yeni bir
    bastırıcı yazarsan onu **hedef sınıfta ve karşıt sınıfta AYRI AYRI ölç**.
  - ⛔ **Kimlik regex'inde `\d` DEĞİL `\d+`**: `-?\d` ⇒ `D-R42`→`D-R4`, `BT-05`→`BT-0`;
    üretilen not **var olan ama alakasız** bir kararı adlandırır (sessiz yanlış-atıf).
  - ⛔ **Fixture'ın YEŞİL olması "bakıyor" demek değildir.** `brifing_lint_d2` **18/18**
    yeşilken kaldırıldı: vektörleri SENTETİK'ti ve tek FP çapası *"fren YAZILMIŞ → sessiz"*
    idi; gerçek korpusta hiçbir salt-okur brifi o dili kullanmıyor ⇒ **kontrol koştu ama
    BAKMADI**. Yeni korpusta FP çapaları **gerçek korpustan çekilmiş** briflerle kurulur.
  - ⛔ Genel arama-tabanlı memory-nudge **ELENDİ, yeniden önerme**: evin kendi `recall_inject`
    skorlayıcısı ajan briflerinde **%100** ateşleyip hedef dersi **0/7** getiriyor (PLAN §8.1).
  - Notlar **ASCII** yazılır (komşu lint notlarıyla aynı konvansiyon, C-ENC-01) ve çapa **ham
    stdout'ta değil çözülmüş `additionalContext`te** kurulur (`ensure_ascii=True`).
  - Kanonik oranlar `governance/infra-changelog.md`'dedir; burada TEKRARLANMAZ.
- watchdog: probes-yok → yalnız reach (SAHTE-ALERT üretme); kopuklukta **1** alert (edge); daemon URL-yoksa graceful-exit; launcher proje-kökünü ARG'la geçirir.
- pre_compact çıktısı `systemMessage` (additionalContext ŞEMA-GEÇERSİZ — canlı-kanıtlı).
- post_tool_failure: fail-payload'da merdiven(+5b infra-satırı) · başarıda sessiz.
- **post_tool_failure ATC P1 SONUÇ ekseni (2026-08-21):** tetik **yapısal alan** — `priority_1_count > 0` ya da `must_fix: true`. ⛔ `findings[]` içindeki `priority` değerlerini ya da mesaj METNİNİ tarama (aynı doktrin: "client_log PROSE'u taranmaz"); ⛔ `other_priority_count` tek başına ASLA konuşturmaz (Prio 2/3 ev politikası gereği kapsam dışı); ⛔ hook politikayı ÜRETMEZ — aracın `policy` alanını TAŞIR, yoksa UYDURMAZ. **Çapa AŞAMASI ÖNEMLİ:** hook `json.dumps` varsayılanıyla basar (`ensure_ascii=True`) ⇒ HAM stdout'ta Türkçe substring aramak **sahte-KIRMIZI** verir; çapa daima çözülmüş `additionalContext` üzerinde kurulur. Hook stdin'i **ham byte** okur (`hook_shim`'in UTF-8 çevirimi `sys.stderr.encoding` KOŞULUNA bağlı ⇒ garanti değil) — bu değişmezin kendi mutasyonu vardır. Korpus: `atc_p1_sonuc` → **22/22**; dört mutasyon: `sayi` 18/22 · `bayrak` 20/22 · `esik` 19/22 · `stdin` 21/22. Eksenin GİRDİSİ `mcp_servers/sap_adt/tools/query.py::adt_atc_check` yanıt şeklidir: alan adı ya da `policy` metni değişirse eksen **sessizce boşalır** (HARİTA'da o dosya da korpusa bağlıdır).
- instructions_log: 10-eşzamanlı → 10-tam-satır; `SEMA-DEĞİŞTİ` görürsen CC-şeması değişti (sessiz `? ?`e dönme).

## B9 — run_all + validator ailesi
- `--quick` süresi: **sabit sayıya değil ŞEKLE bak** — `IX_VALIDATOR_WORKERS=1` seri = paralel **bayt-eş**; 3-koşum bayt-eş. (Sayı bayatlar: 07-31 ölçümü 2,5sn idi; 08-01 tabanı 3,6-3,9sn, V2 uzantı-genişletmesi sonrası 4,3-4,5sn — 52 dosya daha okunuyor. B11 "donmuş sayı" dersinin aynısı.)
- **Bozuk-girdiyle test ZORUNLU:** run_fixture_tests (2026-08-01: 102/102); yeni validator = fixture-çifti de.
- Sınıf-tuzakları: `Path(__file__)`-kök türetme YASAK (project_config kullan; AST-gate yakalar) · `rglob` YASAK → prune'lu walk (SINIF İKİ KEZ yaşandı) · non-ASCII print → `utf8_konsol()` (C-ENC-01) · yeni hook → template-sync (C-TPL-01).
- Yeni gate açılışı: PATTERN#14 (ilk-koşu ölç → taban-sıfırla → HARD).

### B9a — validator ailesi kuyruk-turu (V1-V6, 2026-08-01)
- Altısı tek komutla: `python tests/run_fixture_tests.py` → **102/102** (sayaca değil SATIRLARA bak — mükerrer OZEL_TESTLER satırı sayıyı şişirir).
- MUTASYON ZORUNLU (taban sha `eec3b77`; **HEAD KULLANMA** — commit sonrası HEAD fix'tir):
  `git show eec3b77:scripts/validators/<ad>.py > scripts/validators/<ad>.py` → fixture koş → `git checkout` ile geri al.
  Beklenen: V1 7/17 · V2 8/15 · V3 7/11 · V4 5/11 · V5 9/16 · V6 10/14.
  **0 FAIL görürsen ÖNCE fixture'ın koştuğunu kanıtla** (exit kodu + `2>&1`) — çökme ≠ FAIL.
  📌 YENİ fixture'da bu elle-ezme yerine **fixture-içi `--mutasyon [--ref]`** tercih edilir
  (çalışma ağacı kirlenmez, sayı tekrar üretilebilir) — kurulumu `playbook/howto-infra-fix-proseduru.md` §D2/3.
- ⚠ Mutasyonda GEÇEN vektörler tam da FP-çapaları + kontrol grubu OLMALI. Başkası geçiyorsa iddia sayıya bakıyordur, bulgunun KİMLİĞİNE değil (V1'de yaşandı: `BLOCKER>=1` iddiası eski kodda BAŞKA alandan PASS verdi → check_id+alan-adına çevrildi).
- ⛔ SİLİNMEZ ÇAPALAR: V2 `S3` (`.srvd` naming-glob'unda YOK — `.rules.md` tablo-satırı önkoşul; eklenirse 15 doğru dosya suçlanır) · V5 `N1`/`N7` (core-içi türetilmiş dizinde `.rglob`/`.glob` MEŞRU — geçişlilik taramaya sızarsa 26 FP) · V6 `S3` (`/_[A-Z]` deseni değişmez) · V3 `N4` (`Prior-art: yok` kısa ama meşru) · V4 `N2` (`core/` eşdeğer yazımı).
- Genişletme yaptıysan CANLI ETKİYİ ÖLÇ (PATTERN#14): `CLAUDE_PROJECT_DIR=<proje> python scripts/validators/run_all_validators.py --quick` → taban 0 değilse HARD YAPMA.

### B9b — FS doküman-standardı üçlüsü (DOC-FS-05/06/07, 2026-08-17)
- Tek komut: `python tests/fixtures/fs_docstd/run.py` → **38/38**. Kendi sandbox projesini
  (docs/ + project.yaml + governance/ + validators-local/ + hook_shim + `core` junction'ı)
  temp'te kurar, `finally` ile siler.
- **DOKUZ MUTASYON, hiçbiri diğerini kapsamaz** — hepsi koşulacak; biri tam puan verirse
  korpus O DEĞİŞMEZ için BOŞTUR: `--mutasyon-desen` (A1+A9+A11) · `--mutasyon-katman0` (A2) ·
  `--mutasyon-failclosed` (A6) · `--mutasyon-strict` (A10) · `--mutasyon-esinifi` (A1) ·
  `--mutasyon-baslik` (A11) · `--mutasyon-hook` (B1/B2/B3/B5/B8; **R1-R3 AYAKTA**) ·
  `--mutasyon-express` (X1/X3/X4/Y1; **X5-X9 FP çapaları AYAKTA**) · `--mutasyon-onek` (Y1/Y2).
- **X8/X9 (2026-08-17, canlı ölçümle bulundu):** paylaşılan-infra tespiti üç kollu — ① `/core/`
  junction yazımı ② hook'un KENDİ core'u (`is_relative_to`) ③ **BAŞKA bir core checkout'u**
  (kökünde `CLAUDE.core.md`). ③ olmadan lider ana oturumdan bir core WORKTREE'sini
  düzenlediğinde nudge SESSİZ kalıyordu (② o yolu "dışarıda" görür). X9 çapası şekli aynı ama
  işaret dosyası olmayan ağacın SESSİZ kaldığını ölçer (kör `scripts/validators/` eşleşmesi yok).
- ⛔ SİLİNMEZ FP ÇAPALARI (hepsi ÖLÇÜLMÜŞ bir yanlış-pozitiften doğdu): **A2** temiz FS
  (kapak `| Versiyon | v1.2 |` · başlıksız §1.1 tablosu · §1.3 ilgili-doküman satırı ·
  altbilgi · meşru `L-01/M-02` · ileriye dönük "TS'te canlı ölçülür" · "yazılmıştır") —
  bunlar temizlenemez satırlardır, işaretlenirse gate'in yeşili ERİŞİLEMEZ olur · **A5**
  belgenin KENDİ tanımladığı `H-1` gap ID'sine atıf sayılmaz ama aynı dosyadaki
  "doc-gate M-6" SAYILIR (iç kontrol grubu) · **C4** yalnız büyük/küçük harf değişimi
  "veri kaybı" DEĞİLDİR (Türkçe `İ`.lower() = `i̇` tuzağı; harf standardı T3 ile çakışırdı).
- **Warn-first sözleşmesi (A10):** `--strict` bu gate'te **NO-OP**. `run_all_validators --strict`
  bayrağı tüm validator'lara iletilir; hard'a terfi ADR 0019 §54 gereği AYRI ve bilinçli
  bir karardır. Bulguda exit 1 isteyen tek tüketici hook'tur → `--bulguda-exit1`.
- **Üçüncü değer:** okunamayan dosya = **exit 2** (`[ÖLÇÜLEMEDİ]`), "temiz" DEĞİL (A6);
  `doc_equivalence_check` yol hatası da exit 2 (C3) — eskiden "KAYIP VAR" ile aynı exit 1'di.
- Hook vektörleri GERÇEK giriş noktasından (`hook_shim` + `core` junction'ı) koşar; junction
  kurulamazsa koşucu bunu GÖRÜNÜR bir NOT ile bildirip doğrudan çağrıya düşer (sessizce değil).
- **Y1/Y2 (C-HOOK-01 sınıfı):** nudge metnindeki HER `.md` yolu sandbox proje kökünden
  GERÇEKTEN açılır (metin eşleşmesi değil `is_file()`). `check_hook_injected_paths` yalnız
  `additionalContext` üreten hook'ları görür; **stderr nudge'ları kapsamı DIŞINDADIR** —
  bu iki vektör o boşluğu kapatır. `--mutasyon-onek` ile kanıtlanır.
- **X1-X7 (infra-EXPRESS nudge'ı):** X2 aynı zamanda *erken-return YOK* kanıtıdır (nudge
  susunca akış TRIGGER/HIZLI_KUME'ye devam edip exit 0 verir). X7 komşu-dizin çapası dizin
  YARATMADAN koşar (`resolve()` var olmayan yolu da çözer) — worktree dışına yazılmaz.

## B10 — run_review
- **Tip-haritası tamlığı (en kritik):** her anahtar+eş-anlamlı için `task_for_push()` non-None (None = sessiz-atlama sınıfı).
- Kirli-.bdef → BLOCKER/is_blocker · temiz → PASS · kapsam-dışı prog → task=None (bilinçli).
- SKIP-görünürlüğü: koşmadıysa "PRE-FLIGHT KOŞMADI (sebep)" satırı OLMALI.
- **SKIP sözleşmesi (2026-08-01):** `python tests/fixtures/reviewer_skip_sozlesmesi/run.py` → 11/11.
  Değişmezler: eksik BLOCKER gate → **verdict BLOCKER + exit 1** ("koşmadı" ≠ "temiz"; gate'i
  silmek onu geçmenin yolu OLMAMALI) · eksik WARNING → WARNING/exit 0 · human-mod SKIP'te
  **çökmez ve VERDICT satırını basar** (eski hâli `KeyError: 'stdout'`) · `--json` anahtarları
  `skipped_*`/`failed_*` ile MCP `_reviewer`a taşınır.
  ⚠ **FP çapaları omurgadır:** gate VAR+geçiyor → PASS **ve BOŞ ZİNCİR → PASS**. Boş zincir
  (`dtel_update`, `rap_service_binding`) KAYITLI bir boşluktur; SKIP ile aynı kefeye konursa
  meşru push'lar bloklanır. Kayıtsız eksiklik ≠ kayıtlı boşluk.
  ⚠ Davranış: proje-lokal `check_td_cancelled_fields.py` kurulu DEĞİLSE `struct_creation`
  artık WARNING verir (PASS değil) — kasıtlı görünürlük, bloklamaz.

## B11 — mcp_servers/sap_adt
- Offline: `test_csrf_header_injection` + `test_push_readback_mismatch` + `test_search_objects_type_filter` + import-smoke.
- **ÜÇ-DEĞERLİ DOĞRULAMA (2026-08-01):** `python tests/fixtures/dogrulama_kosamadi/run.py` → **32/32**.
  Değişmezler: silme-readback okunamazsa `delete_verified: null` (**true DEĞİL**) · push readback
  koşamazsa `readback_verified: null` + `readback_notice` (ama `ok` DÜŞMEZ — aşırı-sıkılaşma çapası) ·
  bozuk XML'de `where_used`/ATC/inactive **istisna atar** (boş liste = "temiz" DEĞİL) · `csrf`
  SystemExit ATMAZ (tool `ok:false` döner) · paket-ucu fallback'inde `package_verified:false` +
  `scope_verified:false`. Kontrol grubu satırları (404→verified true, geçerli-boş XML→[],
  biçim-farkı→true, nodestructure→verified true) **silinmez**.
- Profil fail-closed: profil-boz → tools/list yalnız `ping`. ⚠ **Sayı REÇETEDE DONMUŞTU**
  ("19/18/1" = 2026-07-10 ölçümü; yüzey o gün 19 tool'du). 2026-08-01 ölçümü: **s4_private 30 /
  btp_abap 29 / profilsiz 1**. Sabit sayıya değil ŞEKLE bak: `s4_private = btp_abap + 1`
  (`adt_transport_list`) ve profilsiz = yalnız `ping`. ⚠ Ölçüm harness'i: `server.py`'ı import
  etmek TEK BAŞINA yalnız `ping` verir (`_register_all()` `main()` içinde çağrılır) — bu tuzağa
  düşülüp "profil matrisi çöktü" sanıldı; doğrusu `import server; server._register_all()`.
- Varlık-sondası değişmezi: silinmiş-obje → where_used **count-anahtarı DÖNMEZ** (OBJECT_NOT_FOUND).
- unit_run 0-test görürsen ÖNCE KONTROL-GRUBU (SE24); inactive_objects çıktısında `stale_deleted`+`tadir_check` OLMALI — `FAILED`'da "silinmiş değil" VARSAYMA; ⛔ TADIR-DELFLAG satırları silinmez.
- **ABAP KOŞTURAN TOOL AİLESİ — İKİ KAPI (2026-08-28, C-08):**
  `python tests/fixtures/unit_run_guard_riski/run.py` → **11/11 + 5 mutasyon**, exit 0.
  Değişmezler: `adt_unit_run` · `adt_syntax_check` · `adt_classrun` · `adt_post_shell`
  **DÖRDÜ DE** `require_customer_namespace` **ve** `require_writable_tier` çağırır (G3 AST
  çapası — vaka değil SINIF) · kapılar **HTTP'den ÖNCE** (G1b: guardrail dönüşünde POST
  sayısı **0**) · `testRiskLevels` **varsayılan `harmless`**, `dangerous`/`critical` yalnız
  `allow_risky_tests=True` ile · `method_count == 0` + kapalı bant → `risk_notice`
  (⛔ bant AÇIKKEN uyarı YOK — alarm yorgunluğu çapası, R3b silinmez).
  ⚠ `risk_levels`/`risk_notice` alanlarını kaldıran bir "sadeleştirme" bu ekseni **boşaltır**:
  "0 test" ile "0 HARMLESS test" yeniden ayırt edilemez hâle gelir.
  🔴 DOĞRULANAMADI: bandın kapanmasının **canlı** test sayısına etkisi ölçülmedi (fixture
  SAP'ye bağlanmaz). İlk canlı kullanımda `method_count`u SE24 kontrol grubuyla kıyasla.
- **GREP KAPSAM MUHASEBESİ (2026-08-28, C-04):**
  `python tests/fixtures/grep_kapsam_gorunurlugu/run.py` → **14/14 + 5 mutasyon**, exit 0.
  Değişmezler: kapsamdan düşen her obje `skipped_objects` içinde **ad + sebep** ile döner
  (`type_filtered` · `type_unsupported` · `max_objects` · `read_failed` · `not_readable` ·
  `source_empty`) · FUGR okunduğunda `partial_objects: fugr_skeleton_only` (playbook
  `adt-fugr-functions.md §4.1`) · `coverage_complete` **ayrı eksendir**, `scope_verified`in
  anlamını DEĞİŞTİRMEZ (N1/N2 çapaları; `dogrulama_kosamadi` R5 ile birlikte okunur) ·
  tam kapsamda **uyarı YOK** (K2b).
  ⛔ Sebep sınıfları **uydurulmaz**: yeni bir sebep eklemeden önce playbook'ta ölçülmüş
  körlüğü göster (kaynak: `adt-fugr-functions.md §4/§4.1`, `lessons-learned` #19/#20, Q106).
  ⚠ ÖLÇÜM ALETİ NOTU: `object_types` filtresi `_GREP_TYPE_MAP` kontrolünden **ÖNCE** koşar —
  `type_unsupported` dalını ölçmek için filtreye o tipi (ör. TABL) **eklemek** gerekir; yoksa
  iki farklı sınıf tek sebebe (`type_filtered`) düşer ve dal ölçülmemiş kalır.
- **DDIC okuma-yolu (2026-08-09):** `python tests/fixtures/ddic_okuma_yolu/run.py` → **31/31**, exit 0.
  Değişmezler: `table`/`structure` → `/sap/bc/adt/ddic/{tables|structures}/<ad>/source/main`
  **düz DDL** · `dataelement`/`domain`/`tabletype` → XML yolu ve `/source/main` **HİÇ istenmez**
  (o uç bu üç tipte 404 verir → obje YANLIŞLIKLA "yok" görünür) · `adt_get` ile `sap_sync_pull`
  **AYNI** sınıflandırmayı çağırır (tek kaynak: `object_types.ddic_read_mode`) · 404 → `exists:false`
  **ama log'da 404 kanıtı** · 500 → yokluk BEYAN EDİLMEZ · 200+boş gövde → `source_empty`+uyarı.
  ⛔ Yeni bir tipi DDL-uçlu ilan etmeden önce **canlı ölç** (en az bir Z + bir STANDART obje;
  ayrım tipe bağlıdır, Z-olmaya değil). Tip kümesi `scripts/object_types.py`dedir — `atom.py`ye
  ya da `sap_sync_pull.py`ye YEREL KOPYA yazma (fixture AST çapası bunu yakalar; ayrışan iki
  kopya bu kusurun kökündeydi).
  ⚠ Kümeler DÜZ set literali kalmalı (`frozenset(...)` DEĞİL): `reviewer_tip_kapsam` onları
  `ast.literal_eval` ile okur ve çağrı ifadesini çözemez → "tablo okunamadı" FAIL'i verir.
- struct-create sonrası koşulsuz içerik-verify ("activated" shell'i maskeleyemez).
- Canlı-yazma testleri: yalnız gateway + throwaway-Z; eşzamanlı-gateway varken KOŞMA.
- **Tier (ADR 0010) FAIL-CLOSED:** `python tests/fixtures/tier_fail_closed/run.py` → 24/24, exit 0.
  Değişmezler: tier-satırsız `.conn_adt` → `UNKNOWN` (**DEV DEĞİL**) → mutasyon RED ·
  `ADT_SAP_TIER_OLD=DEV` tuzağı (gerçek satırdan ÖNCE **ve** SONRA) tier'ı GASP EDEMEZ ·
  `require_writable_tier(None|"")` REDDEDER (ikinci fail-open katmanı geri gelmesin) ·
  UNKNOWN'da hassas-OLMAYAN okuma SERBEST kalır (salt-okuma kısıtlanmaz) · statusline
  tier-yoksa `TIER-YOK RO` gösterir. Yeni tier kaynağı eklersen fixture'a satır ekle.
- **Veri/yetki guard'ları (ADR 0011 PII + K-2/K-3):** `python tests/fixtures/veri_yetki_guardlari/run.py` → 57/57, exit 0.
  Değişmezler: hassaslık **normalize aday-kümesinde** ölçülür — `KNA1 AS K` / `kna1 k` /
  `SAPABAP1.KNA1` / JOIN'li ifade / `T000, KNA1` / `I_Customer` / `V_KNA1` **BLOK** ·
  alan-seviyesi guard KABLOLU (`columns=STCD1` ve `SELECT stcd1 ...` → BLOK) ·
  **iki tool aynı kararı verir** (`adt_table_read` ↔ `adt_sql_query` eşdeğerlik satırları —
  ayrışma bu kusurun köküydü, yeni tool eklersen o listeye satır ekle) ·
  `adt_syntax_check` PRD/UNKNOWN'da **RED** + standart objede **RED** + özet satırında
  "read-only" YASAK · `adt_lock_check` çözülemezse `locked: null` (**`false` DEĞİL**).
  ⚠ FP-çapaları (T000 · `T000 AS T` · ZSD001_T_* · TADIR · DD02L · /SCWM/AQUA · DEV
  muafiyeti · açık-onay yolu) **omurgadır** — kaldırılırsa guard günlük okumayı bloklar.
  ⚠ Fixture opsiyonel data_guard API'lerini `dg_cagir()` ile çağırır: doğrudan çağrı eski
  sürümde AttributeError → koşucu çöker → mutasyon **0 FAIL** gösterir ("çökme ≠ FAIL").

## B12 — claude_overlay + team_setup + init_project
- **KIYAS TABANI (2026-08-13, en güçlü kapı testi):** `python tests/fixtures/overlay_kiyas_tabani/run.py`
  → **27/27**, exit 0 *(bu satır 23/23 diyordu; korpus V16-V19 ile büyümüştü ve rakam burada
  bayatlamıştı — 2026-08-13'te koşularak düzeltildi. PATTERN #18-h: aynı sayı iki yerde
  yaşarsa biri bayatlar)*. Değişmez: `fark_raporu` **kopya-ŞİMDİ ↔ en son ÜRETİLEN**'i (manifest
  `uretilen_hash`) kıyaslar — "bugün üretilecek içerik"le DEĞİL. Aksi hâlde core'un her
  commit'i, elle düzeltme sıfırken bile kapıyı kapatır (kurt masalı → `--overlay-onayli`
  refleksi → gate kendi koruduğu şeyi ezer).
  ⚠ **Çapaları SİLME:** V3/V4/V6/V7/V9 (elle düzeltme her biçimde DURDURUR) omurgadır;
  V10/V11 **geriye-uyum** çapasıdır (`uretilen_hash`siz veya bozuk manifest → birebir ESKİ
  muhafazakâr davranış; kanıt yoksa gevşeme de yok). K16/K16b/K16c inspector KABLOLAMASI'dır:
  core-bayatlığı TEK bulgu · elle düzeltme hâlâ görünür · **modül import edilemezse SESSİZ
  değil görünür bulgu** (o dal 2026-08-13'e kadar `except: pass` idi — KOŞMADI ≠ TEMİZ).
  ⚠ Fixture'ın sandbox core'u `scripts/utils/claude_overlay.py` iskeletini TAŞIMALI: inspector
  modülü kendisine verilen core kökünden import eder; iskelet yoksa dal hiç koşmaz ve K16b
  **sahte-KIRMIZI** verir (ilk koşumda tam bu oldu). Aynı sınıf: modülü bir kez import ettikten
  sonra dosyayı silmek import'u bozmaz (sys.modules) → K16c önce önbelleği boşaltır.
  ⚠ ÇİFT mutasyon şart (fix eskiyi KORUYUP yeni davranış EKLEDİ; tek mutasyon yarısını sınamaz):
  `--mutasyon` (taban **15e9a51**, ⛔ dal adı değil) → P düşer · `--mutasyon-gevsek` → N düşer.
  ⛔ **ÇIKIŞ KODU SÖZLEŞMESİ — iki modda 0'ın ANLAMI FARKLIDIR** (bu evin `exit 0 ≠ kanıt`
  tuzağı): *normal modda* `0`=tüm vektörler geçti · `1`=en az bir vektör düştü · `2`=alet
  geçersiz (taban alınamadı / mutasyon çapası tutmadı / iki mod birden) — hiçbir sayı basılmaz.
  *Mutasyon modlarında* `0` = **ölçüm GEÇERLİ**, "düşen yok" DEMEK DEĞİLDİR (düşmek zaten
  beklenen sonuçtur) → kararı `N/M OK` satırından ve hangi vektörün düştüğünden oku, exit'ten
  DEĞİL. `2` her iki modda da aynı: ölçüm yapılamadı.
  ⚠ Ş2 çapası **V16**: `kaynak: proje` dosyası silme dalında HER DURUMDA kapıda kalır —
  gevşetme yalnız core-üretimi artıklara uzanır (V16 **her iki mutasyonda da ayakta**, yani
  aşırı-gevşek taban altında bile korunuyor). **V17** üçüncü vaka sınıfının çapasıdır
  ("üretilmiş + bilinçli ÖZELLEŞTİRİLMİŞ", emsal `.github/CODEOWNERS`+`<OWNER_TEAM>`):
  overlay'de özelleştirmenin AYRI doğruluk-kaynağı (`claude-local/`) olduğu için beklenen
  içerik zaten özelleştirilmiş içeriktir → drift sanılmaz, normalizasyona ihtiyaç YOK.
  **V18/V19** normalizasyon sınırını kilitler: taban BAYT-BAYT'tır (kasıtlı — o baytları biz
  yazdık, sapma dışarıdan dokunuş kanıtıdır); saf CRLF gürültüsü bir alt katmanda `_norm`'lu
  içerik-kıyasında emilir (V18), CRLF + kaynak değişimi birlikte gelirse muhafazakâr davranır
  ve `durum()` CRLF'i ayrıca raporlar (V19 = bilinen sınır, yönü güvenli).
- **OTOMATİK TAZELEME (2026-08-13 ikinci yarı):** `python tests/fixtures/overlay_oto_tazeleme/run.py`
  → **33/33**, exit 0. Otomatik yol **yerinde senkron**dur (rmtree YOK; `materyalize` yalnız elle yolda). Değişmez İKİ tanedir ve ayrı ayrı sınanır: **① EYLEM** — fark boşsa
  kopya kullanıcı komutu olmadan üretilir · **② İMTİNA** — fark doluysa hiçbir şeye
  dokunulmaz. Üçüncü değişmez **GÖRÜNÜRLÜK**: her iki dal da satır basar; V19 meta-vektörü
  *"diski değiştiren her dal satır basar"*ı dört senaryoda birden ölçer (sessiz davranış =
  denetlenemeyen davranış).
  ⚠ **ÇİFT mutasyon ŞART:** `--mutasyon` (taban **63e6faa**, ⛔ dal adı değil) → P düşer ·
  `--mutasyon-gevsek` → N çapaları düşer. **Gevşek mutasyon İKİ çapa keser** (`oto_tazele`
  ön-kontrolü + `_yerinde_senkron`'un iç kapısı): kapı iki katmanlıdır, tek-noktalı mutasyon hedefi ıskalar ve
  koşucu sayı BASMAZ (exit 2 — bu doğru davranıştır, alet arızası değil). Çıkış-kodu
  sözleşmesi kıyas-tabanı fixture'ıyla AYNI (yukarı bkz).
  ⚠ **Çapaları SİLME:** V3/V4/V10/V16 (elle düzeltme her biçimde DURDURUR) · **V7** (core
  okunamıyorsa DOKUNMA — otomatik üretim orada tüm kopyaları SİLERDİ) · **V20** (savunma
  derinliği: `materyalize(onayli=False)` kapıyı kendi içinde de tutar) · **V11** (geri-alma:
  `IX_OVERLAY_OTO=0` otomatiği tümüyle kapatır) · **V22** (ATOMİKLİK: `oto_tazele` çağrı zincirinde rmtree/materyalize YOK — AST çapası; olmazsa biri otomatiği tekrar `materyalize`'e bağlar ve SESSİZ olur) · **V21** (ilk materyalizasyon = kurulum işi, otomatiğe dahil DEĞİL) · **V2d** (idempotans — yordam ile üretici
  ayrışırsa her açılışta kendini tetikleyen sonsuz tazeleme olur).
  ⚠ **Sandbox core `scripts/utils/claude_overlay.py` iskeletini TAŞIMALI** (K20-K24 gerçek
  `session_start` alt-sürecini koşar ve hook modülü KENDİNE VERİLEN core kökünden import
  eder). İskelet yoksa import düşer, hook yalnız junction uyarısı basar ve K20/K21
  **sahte-KIRMIZI** verir — ilk koşumda tam bu oldu.
  📌 **İDDİA SINIRI:** tazeleme **bir SONRAKİ oturumdan** itibaren etkilidir (ajan tanımları
  oturum başında okunur; canlı harness'ta 3 koşumla ölçüldü — changelog'daki ÖLÇÜLMÜŞ SINIR
  bloğu). Fixture bunu doğrudan ölçemez (harness gerekir); ölçtüğü şey diskteki sonuç +
  hook çıktısındaki duyurudur.
- **MATERYALIZE ATOMIKLIGI (2026-08-27, Q30 kayip vakasi):**
  `python tests/fixtures/overlay_materyalize_atomik/run.py` → **24/24**, exit 0.
  Degismez IKI tanedir ve AYRI olculur: **① ATOMIKLIK** — `materyalize` dizini SILMEZ
  (uzerine yaz → fazlaligi tek tek sil → manifest en son); en kotu halde eski+yeni karisimi
  kalir, **hicbir noktada BOS kalmaz**. **② DURUSTLUK** — uretim kendi ciktisini olcmeden
  BASARILI demez (kanit kapisi: `core/claude/<tip>` okunamiyorsa DOKUNMA · son-durum
  oz-denetimi: eksik/frontmatter-bozuk dosya varsa `ok=False` + **elden gecirilecek dizin
  adiyla** yazilir).
  ⚠ **CIFT mutasyon SART** (tek mutasyon ikisini ayirt edemez): `--mutasyon` (taban
  **d51ba09**, ⛔ dal adi degil) → **10/24**, P+D+G+K3 duser, **N1-N8 + K1 + K2 ayakta** ·
  `--mutasyon-gevsek` (yalniz ② sokulur) → **19/24**, dusen **P3b/D1/D1b/D2/D3** ⇒ D vektorleri
  atomiklikten BAGIMSIZ olcuyor. Oz-denetim: taban `materyalize`inde rmtree yoksa hicbir sayi
  ⚠⚠ **N8 PLATFORM-BAGIMLIDIR (2026-08-29 ileri-fix 2, CI run 33267199186):** N8 junction->dizin donusumunu olcer. Taban `d51ba09:224` **ciplak `os.rmdir`** cagirir; POSIX'te symlink dizin girdisi DEGILDIR => `NotADirectoryError`. Onceden bu istisna disari cikip **kosucuyu cokertiyor ve 30+ vektorun hepsini siliyordu**; artik `--mutasyon` kipinde `N8 ATLANDI/BILINEN` diye **etiketli PASS**tir => yukaridaki *“N1-N8 ayakta”* pini Windows'ta da Linux'ta da **ayni** okunur. Windows'ta dal hic tetiklenmez (junction = gercek dizin) => kusur yerelde **gorunmez**.
  🔁 **Linux ikizi olmadan dogrula (`--taklit-posix-symlink`; kip DEGIL, batarya kesfi gormez):** `os.rmdir`i yalniz N8 cagrisi boyunca `NotADirectoryError` attirir. Uc kontrol: (1) yakalayici sokulunce `--mutasyon --taklit-posix-symlink` -> **exit 2 + `kosucu coktu`** (CI semptomu birebir; pozitif kontrol SART, yoksa assertion yalanci) (2) fix'li -> **10/24** + etiketli satir (3) **mutasyon DISI** + ayni bayrak -> **24/24**, N8 ATLANMAZ (muafiyetin DAR oldugunun kaniti).
  BASILMAZ (exit 2). Cikis-kodu sozlesmesi kardes overlay korpuslariyla AYNI.
  ⚠ **Capalari SILME:** N5/N6 (T2.5 kapisi + onayin anlami) · N7 (fazlalik `.md` hala silinir
  — atomiklik "hic silme"ye donusmesin) · N8 (junction→gercek dizin donusumu; CORE hedefi
  dokunulmaz) · **K1** (komsu V22'nin ikizi: `oto_tazele` zincirinde `materyalize` YOK —
  iki fonksiyonu "DRY" diye birlestiren biri bu satiri kirar) · **K3** (kablolama:
  `team_setup.junctions` tip-basina yalitim; olculen zarar tek tipteki istisnanin kurulumun
  kalan 5 adimini atlamasiydi).
  ⚠ **D3 = 3.BAGLAM GERCEK SEKIL capasi:** `core/claude/skills` dizin-tabanlidir
  (`<skill>/SKILL.md`), kokunde `*.md` YOKTUR. Overlay mekanizmasi bastan sona `*.md`
  glob'una dayanir ⇒ bir proje `claude-local/skills/` acarsa uretilecek kume core
  skill'lerini icermez. Bu satir silinirse o sessiz kayip yolu geri acilir.
  ⚠ **G1/G1b = GEVSETME capasi:** yeni kod `.md` DISI dosyalari artik SILMIYOR (eski `rmtree`
  siliyordu) ama mesajda **adlariyla listeliyor**. Bu satirlar silinirse daralmanin siniri
  olcusuz kalir.
  ⚠ **Sahte `shutil` GERI ALINABILIR enjekte edilmeli** (`_shutil_enjekte`): taban surumde
  `shutil` GERCEK bir modul niteligidir, korumasizca `delattr` edilirse sonraki vektor
  `NameError` ile coker ve kosucu **KURULAMADI'yi KACTI gibi** gosterir (ilk kosumda tam bu
  oldu).
- Bayraksız senkron → fark-listesiyle **RED**; yalnız `--overlay-onayli` ezer.
- FORMAT-GATE: her .md `---` ile başlar + CRLF-yok + name-parse + damga-frontmatter-SONRA ("sayı ≠ yüklenebilirlik" — 6/6 düşüş vakası).
- Drift: core-değişti→WARN · yeni-agent→EKSİK · temiz→PASS.
- **Template-provası (en güçlü):** template_project'i sıfırdan üret → "bugün koşsa geride proje üretir mi?"
- Worktree yalnız `--provision-worktree`.

## B13 — core_precommit + pre-commit
- `--all` (CI-eş); zorla-stage `core/leak.md` → exit 1; sır-kilidi 4-senaryo (alt-dizge-tuzağı dahil).
- Kablolama: `git config core.hooksPath` unset ise hook SESSİZCE hiç koşmaz (bunu zorlayan gate YOK — bilinçli-bilinen boşluk).
- Changelog-gate (4. kontrol): `python tests/fixtures/changelog_gate/run.py` → 13/13, exit 0.
  Kapsar: infra-staged+kayıtsız→BLOK · kayıtlı→SERBEST · yalnız-doküman→SERBEST · `IX_NO_CHANGELOG=1`
  kaçışı (SESSİZ değil, uyarı basar) · `tests/fixtures/**` muaf · `--all`/CI'da SUSAR ·
  **GERÇEK commit BLOK + kayıt eklenince GERÇEK commit GEÇER** (sentetik ayrı git reposu).
  ⚠ Tarihçe: bu kapı 2026-08-01'de "eklendi+test edildi" diye YAZILDI ama kodu merge edilmedi
  (`reset --hard` kaybı); 2. denemede fixture'la birlikte geldi. **Fixture'sız gate kaybolur** —
  kapıyı elden geçirirken önce bu fixture'ı koş, "kod duruyor mu" diye BAKMA (`infra-changelog.md`
  → core_precommit bölümü dürüstlük notu).

## B13b — build_core_index (CORE-INDEX kapsamı)
- `python tests/fixtures/core_index_kapsam/run.py` → 10/10.
- Değişmezler: `governance/` DÜZ dosyaları (infra-changelog + infra-test-recipes DAHİL —
  F0'ın zorunlu okuması) indekste · **mükerrer satır YOK** (governance'ı `rglob` ile eklemek
  `decisions/`i çiftler) · üretilmiş `CORE-INDEX.md` kendini listelemez · `scripts/`,
  `mcp_servers/`, `tests/` indekse SIZMAZ (kod ≠ doküman) · indeksteki her yol diskte var.
- **Değiştirdiysen `python core/scripts/build_core_index.py` YENİDEN KOŞ** — yoksa
  `check_core_index_fresh` (C-IDX-01) BAYAT der. Damga satırı kıyasta yok sayılır.
- ⚠ Ölçüldü (2026-08-01): DEV_CORE'un KENDİ `governance/CORE-INDEX.md`'si bayat kalabiliyor;
  gate'in core deposunda fiilen koşup koşmadığı ayrı bir denetim kalemidir.

## B17 — Claude Code proje-slug'ı (auto-memory / transcript adresleri)
- `python tests/fixtures/proje_slug_tek_kaynak/run.py` → 7/7. TEK KAYNAK:
  `scripts/utils/claude_paths.py` (`proje_slug`/`transcript_dizini`/`auto_memory_dizini`).
- Kanonik kural: **alfanümerik olmayan HER karakter `-`** — alt çizgi DAHİL
  (`C:\IX\DEV_CORE` → `C--IX-DEV-CORE`).
- ⚠ **Kanıt kuralı:** konvansiyonu `~/.claude/projects/` altındaki dizin ADLARINA bakarak
  doğrulama — orada bizim script'lerimizin yarattığı dizinler de var (dairesel kanıt; bu
  tuzağa bir kez düşüldü). Yer gerçeği `*.jsonl` içindeki `cwd` alanıdır: transcript'i
  OLMAYAN dizini Claude Code yazmamıştır. Ölçüm: A 4/4, B 2/4.
- Yeni bir tüketici eklersen slug'ı YENİDEN TÜRETME; fixture'ın V3/V4 vektörleri yakalar.

## B18 — deploy_ui `--all-changed` (git sorgusu)
- `python tests/fixtures/git_sorgu_sessiz_bos/run.py` → 6/6 (gerçek sentetik git repoları).
- Değişmez: git ARIZASI ("fatal:", exit≠0) **asla** "değişen app yok"a çevrilmez → exit 1 +
  sebep + `--app/--apps/--all` alternatifi. Tetikleyiciler: tek-commit'lik repo, `--depth 1`
  shallow clone, git ağacı olmayan dizin.
- FP çapası: sağlam repoda app bulunur; son commit `ui/` DIŞINDAysa boş liste MEŞRU kalır.

## B18b — deploy_ui `--dry-run` ÖZET SATIRI (koşmayan doğrulamayı beyan etme)
- `python tests/fixtures/sessiz_olumsuzlama_2026_08_10/run.py` → 29/29 (D bölümü).
- **Değişmez:** özet satırı ÜÇ-yollu olmak zorunda (banner zaten öyleydi). `--dry-run`
  canlıya HİÇ bakmaz (`deploy_one`: `if dry: return`) → çıktısında **"doğrulandı"** ve
  **"canlı =="** sözcükleri GEÇMEZ. Bunun yerine ne yapmadığını söyler + `--verify-only`e
  yönlendirir.
- **Neden kritik:** bu script'in var olma sebebi *"'Successful' mesajına güvenme, içeriği
  kanıtla"*dır; kendi özet satırının koşmayan bir doğrulamayı beyan etmesi **kapının
  kendisini yalanlar**. Ölçülen bedel 2026-08-10: app STALE'ken satır "güncel" sanıldı.
- FP çapaları (SİLİNMEZ): gerçek deploy → *"canlı Component-preload == build çıktısı"*
  HÂLÂ basılır (D2) · `--verify-only` → *"canlı == mevcut kaynak"* HÂLÂ basılır (D3).
  İkisi de kalkarsa fix, mesajı düzeltmek yerine SİLMİŞ olur.

## B18c — transport listesi / kilit sondası / lock sentinel'i (sessiz olumsuzlama)
- `python tests/fixtures/sessiz_olumsuzlama_2026_08_10/run.py` → 29/29 · MUTASYON
  `--mutasyon` (varsayılan `--ref 990f71b`) → **11/29**. 29/29 verirse test BOŞTUR.
  ⚠ `--ref`e DAL ADI VERME (D2/5); taban öz-denetimi yanlış tabanı yakalar → **exit 2**.
- **Üç değişmez:**
  1. `list_user_transports` — parse/ağ hatası `[]`e ÇEVRİLMEZ (`SAPTransportError`);
     eşleşme namespace-BAĞIMSIZ (12 Accept header ⇒ 12 olası şekil); gövde tanınan bir
     tm feed'i değilse **sıfır İDDİA EDİLMEZ**.
  2. `is_object_locked` — **HTTP 404 `locked:False` DEĞİLDİR** (`None` döner). İç kontrol
     grubu: aynı dosya `lock_object`'te 404'ü *"endpoint not found"* okur.
  3. `lock_object` — TÜMÜ 404 ise `NO_LOCK_SUPPORT` (eski davranış); **en az bir non-404
     varsa `SAPLockError`**. Sentinel bir karar olmalı, varsayılan değil.
- ⚠ **FP çapaları OMURGA — özellikle C1** (tümü 404 → `NO_LOCK_SUPPORT`): kaldırılırsa
  kilit ucu OLMAYAN sistemlerde TÜM push'lar kapanır = **#99'un birebir tekrarı**
  (ölçülmüş maliyet: 5 deneme / ~1 saat + kullanıcı boşuna SE24'e yönlendirildi).
  Diğerleri: A5 (geçerli-boş feed → 0, hata yok) · B2 (200 + kilit yok → `locked:False`;
  yoksa araç hiçbir zaman "kilitli değil" diyemez).
- 🔴 **CANLI DOĞRULAMA LİDER/GATEWAY İŞİ:** korpus HTTP katmanını sahteleştirir.
  `/sap/bc/adt/locks` ucunun bu sistemde gerçekten ne döndürdüğü **DOĞRULANAMADI**.
  Fix her iki hâlde de dürüst: uç cevap veremezse `locked:null`, "kilitli değil" DEMEZ.

## B18e — `_find_existing_transport` ("Bug 11 sessiz fallback")
- `python tests/fixtures/sessiz_olumsuzlama_2026_08_10/run.py` → 40/40 (F bölümü) ·
  MUTASYON → 16/40.
- **Değişmez:** sorgu başarısız olduğunda **fallback KORUNUR ama SESSİZ DEĞİLDİR** —
  görünür `[WARN]` + statü + *"bu bir DOĞRULAMA DEĞİL, VARSAYIMDIR"*. Sonuç ayrıca
  `_last_transport_lookup` ile makine-okunur (`resolved`/`kept`/`no_entry`/`foreign_only`/
  `shape_unrecognized`/`error:<Ad>`).
- ⚠ **F2 FP ÇAPASI OMURGADIR:** hata hâlinde HÂLÂ `requested_transport` döner. Bu vektör
  silinir ya da fix `raise`e çevrilirse **E071 erişimi olmayan her sistemde her push
  kırılır**. Fallback bir kusur değil TASARIMDIR; kusur SESSİZLİĞİYDİ.
- ⚠ **FP ÇAPASI ile AYIRT EDİCİYİ AYNI VEKTÖRDE BİRLEŞTİRME.** İlk yazımda F4-F7'ye
  `durum == ...` şartı da konmuştu; `_last_transport_lookup` fix'le GELDİĞİ için dördü de
  mutasyonda düştü — yani "FP çapası" etiketli oldukları hâlde fiilen ayırt edici
  davranıyorlardı ve *"doğru çalışan vaka bozulmadı"* kanıtı yok olmuştu. Davranış (F4-F7)
  ile teşhis-alanı (F9) **ayrıldı**; geri birleştirme.
- **BİLEREK DÜZELTİLMEYENLER:** `:343` (sütun var, satır yok = yeni obje) ve `:368`
  (adaylar başkasının = transport gaspı yasağı) — ikisi de MEŞRU kurtarma, yanıltıcı
  değil. Triyaj ölçütü: *"cağıran meşru olumsuzdan ayırt edemiyor MU + bu olumsuz bir
  KARARI besliyor MU"*; ikisi birden yoksa dokunma.

## B18d — sınıf alt-include'u push'u (ccau/ccimp/ccdef/ccmac)
- `python tests/fixtures/class_include_push/run.py` → 15/15 · MUTASYON → **1/15**.
- **Değişmez:** yaratım ve içerik AYRI ADIMLARDIR. include YOK → POST(iskelet)+PUT(gövde);
  include VAR → yalnız PUT (var olana POST **500**). **POST gövdeyi YOK SAYAR** (ölçüldü:
  11.639 → 56 bayt) ⇒ **readback ZORUNLU**, opsiyonel değil.
- Sahte-yeşil bekçisi (V8): tüm HTTP kodları 200/201 olsa BİLE içerik iskeletse readback
  hata verir. Bu vektör kalkarsa `adt_unit_run` `method_count=0` sınıfı geri döner.
- ⚠ **ÇÖKME ≠ FAIL (D2/2) bu fixture'da BİZZAT yaşandı:** detay dizgeleri eagerly kurulur;
  mutasyonda `mevcut=None` → `None.encode()` koşucuyu çökertti ve mutasyon "sonuç yok"
  verdi. `bayt()`/`kirp()` yardımcıları bunun için var — SİLİNMEZ.
- 🔴 **DOĞRULANAMADI:** statüler `playbook/adt-classes.md §24.8`'in 2026-07-29 canlı
  ölçümünden; fixture SAP'yi TAKLİT eder. `testclasses` DIŞINDAKİ segment adları bu evde
  canlı ölçülmedi — `CLASS_INCLUDE_TYPES[...]['olculdu']` bunu beyan eder, **V11 beyanın
  doğruluğunu denetler**. İlk kullanan canlı doğrular ve alanı günceller (tahmini
  "olculdu" YAZMA).
- İlk gerçek kullanımda kabul ölçütü: `adt_get` → include listesinde segment VAR MI ·
  kaynağı **bayt olarak** repo ile kıyasla · `adt_unit_run` → `method_count == beklenen`
  (**0 = FAIL**, "yeşil döndü" yetmez).

## B19 — .conn_adt YAZICI tarafı (encoding)
- `python tests/fixtures/conn_yazici_encoding/run.py` → 7/7 (locale-bağımsız).
- Değişmez: `.conn_adt` yazan her yol AÇIK `encoding="utf-8"` taşır (AST çapası tüm
  `write_text` çağrılarını denetler). Okuyucular utf-8/utf-8-sig; yazıcı locale'e bırakılırsa
  cp1252'de em-dash → `0x97` → **her `import sap_adt_lib` çöker** (1085 baytlık dosya vakası).
- ⚠ Şablondaki non-ASCII karakter KANARYADIR; ASCII'ye indirgersen test sessizce boşalır (V6).
- FP çapası: dosya BOM ile BAŞLAMAZ (BOM eklemek AV-02 sınıfını geri getirir).

## B20 — lock yanıtı `MODIFICATION_SUPPORT` (sap_adt_lib `_verify_and_return_lock`)
- `python tests/fixtures/lock_modification_support/run.py` → **29/29** · MUTASYON:
  `--mutasyon` → **17/29** (12 ayırt edici FAIL). Taban **`b9c1a0b`** (varsayılan).
- 🔴 **MUTASYON REF'İNE DAL ADI VERME — ÖLÇÜLDÜ (2026-08-10).** Reçete eskiden
  `--ref origin/main` diyordu; fix merge edilir edilmez `origin/main` **"fix SONRASI"na kaydı**
  ve aynı komut **17/29 yerine 26/29** döndü: korpus ayırt etmiyormuş gibi göründü, **hata
  vermeden**. Mutasyon tabanı, kusurun CANLI olduğu **SHA'ya çivilenir**. Koşucu artık tabanı
  **öz-denetler** (NoModification gerçekten fırlatıyor mu?) ve geçersizse **exit 2** ile durur —
  `exit 1` (vektör düştü) ile karıştırılmasın; hiçbir sayı raporlanmaz.
  ⇒ Genel kural: **her mutasyon korpusu tabanını pinlemeli ve tabanın kusurlu olduğunu
  doğrulamalı** — yoksa fix merge olduğu gün korpus sessizce ölçmeyi bırakır.
- 🔴 **SÖZLEŞME 2026-08-10'da TERSİNE DÖNDÜ — bu bölümün eski hâli "yalnız `NoModification`
  hata verir" diyordu; O KAPI YANLIŞ-POZİTİFTİ ve tüm class-push'u kapattı.** Bugün:
  **HİÇBİR değer akışı KESMEZ.** Ölçüm: CLAS 5/5 `NoModification` (hepsi başarıyla push
  edildi) · DDLS 3/3 boş ⇒ değer tip-bağımlı NORMAL çıktı, ayırt edici DEĞİL. (§12.7b)
- **Tanıma yine de ölçülür ve TAM EŞİTLİKTİR** — ama artık "hata verdi mi" ile değil,
  **çıktıdaki İZ (`§12.7b`)** ile: `NoModification` + casefold varyantları İZ basar (V1c/V7);
  `NoModificationAllowed` / `PartialNoModification` / `No Modification` / `Something` / boş /
  alan-yok İZ **basmaz** (V4/V6/V8). ⚠ İz kontrolünü kaldırırsan V8 **sessizce anlamsızlaşır**
  (hiçbir şey hata vermediği için "sonuç=ok" testi her koşulda geçer) — alt-dizgeye kayma fark edilmez.
- **Kilit BIRAKILMAZ** (V1b): akış sürüyorsa kilidi bırakmak PUT'u 423'e mahkûm eder.
- **§12.7 teşhisi 423'te basılır**, ortak helper `put_423_diagnosis` (V16/V16b/V20): E071
  sorgusu + **iki kök** (transport kaydı **ve** bayat lock handle). 500'de basılmaz (V17 FP
  çapası). Tek kök dayatmak 2026-08-09'da bir saat kaybettiren sapmanın kendisiydi.
- ⚠ **ÜÇ PUT yolu vardır, `set_object_source` yalnız biridir:** `push_textpool.py` ve
  `sap_set_object_description.py` **kendi PUT'unu atar**. Yeni bir PUT yolu eklersen 423
  dalına helper'ı bağla — V21 (statik) bunu bekçilik eder, V21b metnin kopyalanmasını yasaklar.
  `push_textpool`'da helper'a **`te_url`** ver (`.../source/<altad>` biten URL obje adını
  yanlış çözer → E071 sorgusu yanlış ada bakar).
- ⚠ V21/V21b **STATİK**: "referans var" der, "koştu" demez. Kaynağı modülle aynı yerden okur
  (mutasyonda `git show <ref>`) — çalışma ağacını okusalardı mutasyonda sahte-PASS verirlerdi.
- Bozuk XML dalı **görünür iz** basar ("NOT verified") — sessizleştirmek §127 sınıfına düşmektir.
- ⚠ Gövde şekli 2026-08-09 CANLI ölçümünden alındı (self-closing BOŞ alan = SAĞLIKLI DDLS);
  V15 kanaryası iskeleti korur.
- **3. bağlam = `clear_enqueue_lock` (V19):** ayrı public API + **sessiz başarısızlık** sınıfı
  (istisnayı yutup `False` döner). Fırlatan sürümde bu araç da her sınıfta görünmeden bozuktu.

## B14 — inspector
- `--self-test` 5/5-FAIL-üretmeli `[✓]` (üretmezse ALET bozuk); `--json`; çıplak-✓ YASAK (kesir basılır).
- B5 üçlü-kıyas: kasıtlı-sapma→1, düzelt→0. "guard-koştu-mu" ÖLÇÜLEMEZ kalemi BİLİNÇLİ — heartbeat ekleme.

## B15 — ui-smoke
- SAP'siz: `npx playwright test --config=selftest.config.ts` (helpers 4-test; ana-config'e dokunmaz).
- Canlı: paket-`ui/`den `start-noflp` + `run_ui_smoke.py --port 8099` (lockout-safe auth; ısrarlı-popup+lrep-401=hesap-kilidi).
- **Kök çözümlemesi (2026-08-10):** `.conn_adt` PROJE kökünde → `project_root()` (env→cwd), `__file__` DEĞİL.
  Korpus `tests/fixtures/conn_adt_proje_koku/run.py` → 13/13 · `--mutasyon --ref add889c` → 6/13.
  Sarmalayıcı ölü olsa da playwright'ın kendisi sağlam olabilir → **kontrol grubu**: `SMOKE_BASE_URL`+`SAP_USER`/`SAP_PASS` env'iyle `npx playwright test` doğrudan.
  ⚠ **"Kimlik bulundu" ≠ "gate çalışıyor"** — uçtan uca kanıt şart: app ayaktayken `run_ui_smoke.py --port <N>`
  → `[ok] auth …(401 değil)` + `N passed` + exit 0 (2026-08-10 ölçümü: **6 passed**, `$metadata` 200).
  ⚠ Ayrı checkout'ta (worktree) `node_modules` YOKTUR → `npx` paketi indirmeye kalkar; kurulu kopyayı
  geçici junction'la bağla, ölçüm sonrası **kaldır** (silme hedefe sıçramasın diye).
- UI5: `.click()` tetiklemez → firePress+model-API; basic-auth header'la; app-içi npm-install YASAK.

## B16 — templates + agents
- Brifing-lint 3-varyant (temiz/şablonsuz/kısa-muaf); Türkçe-FP çıkarsa ÖNCE B1-mojibake.
- **Model beyanı ≠ fiilî:** aynı-oturum spawn oturum-modelini kullanır (tanımlar oturum-başı) → fiilî-doğrulama YENİ oturumda, transcript'ten.
- check_settings_template_sync + check_rule_gate_coverage yeşil (çakışan checklist-no böyle yakalandı: FE-38→39).

## B21 — guard TETİK sözleşmesi (`claude/workflows/guard.template.yml` + `.github/workflows/`)
```bash
python tests/fixtures/workflow_tetik_dupe/run.py          # 9/9 beklenir
# MUTASYON (zorunlu): şablondaki `    branches: [main]` satırını SİL → 6/9, exit 1
```
- **Değişmez:** `push:` DALSIZ bırakılmaz. Dalsız `push:` + `pull_request` = PR dalına atılan
  her push'ta AYNI head SHA iki koşuda doğrulanır (2026-08-13'te 5 PR döngüsünde ölçüldü).
- **Kontrol grubu hazır:** DEV_CORE'un kendi `core-ci.yml`'i baştan beri doğru desende →
  fixture V6 onu okur; V6 kırmızıya dönerse fix yanlış yöne genişletilmiştir.
- ⚠ **`import yaml` YAZMA** — repo pyyaml taşımaz (core-ci yalnız requests/urllib3/python-dotenv
  kurar); `on:` çözümleyicisi bu yüzden elde yazılmıştır. PyYAML'lı çapraz kıyas LOKAL kanıttır.
- ⚠ **CI YAML'ı lokalde koşturulamaz** → asıl doğrulama merge SONRASI canlıdır:
  `gh run list --repo <ORG>/<PROJE_REPO> --workflow guard.yml` çıktısında **`ev=push br=<feature>`
  satırı OLMAMALI**; döngü başına 2 koşu (pull_request + main-push) görülmeli.
- ⚠ **Şablon→proje yayılımı GATE'Lİ DEĞİL:** C-TPL-01 (`check_settings_template_sync`) yalnız
  `settings.template.json` hook envanterini denetler; `guard.yml` kopyaları ELLE senkronlanır.
# EKLENECEK REÇETE — `core/governance/infra-test-recipes.md`

> **Lider için:** `## B9 — run_all + validator ailesi` bölümünün altına, `### B9b`'den **sonra**
> ekle (aynı ailenin üçüncü alt-reçetesi).

---

### B9c — FM imzası ↔ kılavuz senkronu (CLC-SCR7, 2026-08-18)

- **Tek komut:** `python tests/fixtures/fm_imza_doc_sync/run.py` → **11/11**. Her vektör kendi
  sandbox'ını kurar (sahte proje kökü: `project.yaml` + `SOURCE_CODES/…/*.func.abap`; sahte core
  kökü: `playbook/*.md`) ve `finally` ile siler. Gate GERÇEK dosyasından koşar.
- **BEŞ MUTASYON — hiçbiri diğerini kapsamaz** (biri tam puan verirse korpus o değişmez için
  BOŞTUR). ⚠ **KİP BİÇİMİ 2026-08-29'da DEĞİŞTİ (kayıt Q210):** eski `--mutasyon <ad>` (iki
  argüman) **KALDIRILDI** — batarya keşfi tek-argüman biçimini tanır, eski biçimde bataryanın
  değersiz çağrısı `IndexError`/Traceback üretiyordu. Yeni biçim ve **ölçülen** pinler
  (2026-08-29, taban 11/11):

  | kip | sonuç | düşen vektör(ler) |
  |---|---|---|
  | `--mutasyon-capa` | 10/11 | V8 |
  | `--mutasyon-eksik` | **9/11** | V1 **+ V2** (tek vektör DEĞİL — eski reçete yalnız V1 diyordu) |
  | `--mutasyon-hayalet` | 10/11 | V4 |
  | `--mutasyon-failopen` | 10/11 | V5 |
  | `--mutasyon-blok` | 10/11 | V9 |

  Mutasyon **TAM-EŞLEŞMELİ** metin cerrahisidir; çapa 1 kez geçmiyorsa koşucu **exit 3 ile
  DURUR** (sessiz no-op mutasyon = sahte YEŞİL). Geçersiz/eski kip → `[KULLANIM]` + **exit 1**.
  ⛔ Bu pinler **2026-08-29'a kadar DOĞRULANAMAZDI**: mutasyon kipi Traceback veriyordu ve
  süit yalnız TABANI koştuğu için hiçbir kapı görmüyordu.
- **ÜÇ DURUM AYRIMI korpusun çekirdeğidir** ("bakamadım" ≠ "temiz"): V5 blok yok → **exit 2** ·
  V6 belge dosyası yok → **exit 2** · V8 imza ayrıştırma **çapası** (`IV_PROGRAM`) düştü →
  **exit 2** (aksi hâlde 0 fark = sahte `[OK]`) · V7 ABAP kaynağı yok → **exit 0 + `ATLANDI` +
  sebep** (kayıt başka projeye ait olabilir; sessiz OK basılmaz).
- ⛔ **SİLİNMEZ FP ÇAPALARI:** **V9** blok DIŞINDAKİ `IS_LAYOUT`/`IT_OUTTAB` gibi BAŞKA API
  parametreleri HAYALET sayılmaz (belgelerde ALV örnek kodu rutin olarak geçer — blok sınırı
  bu yüzden var) · **V10** aynı token'ın markdown biçim varyantları (`**IV_DYNPRO**`,
  `` `IV_CUA_MERGE` ``, `### IV_PROGRAM`, `<b>IT_BUTTONS</b>`) **belgeli** sayılır (sayaç,
  saydığı şeyin biçim varyantlarına karşı test edilmeden kanıt değildir) · **V11 ÜÇÜNCÜ BAĞLAM**
  farklı imza ŞEKLİ (`REFERENCE(...)` + `CHANGING` bölümü + imza içi yorum satırları + karışık
  harf düzeni) doğru ayrıştırılır.
- **Warn-first sözleşmesi:** `--strict` **NO-OP** (`run_all_validators --strict` bayrağı tüm
  validator'lara iletilir; terfi ADR 0019 §54 gereği ayrı karar). Bulguda exit 1 isteyen
  tüketici `--bulguda-exit1` verir (V2 bunu ölçer).
- **Gerçek-bağlam kontrolü (fixture DIŞI, gerekince tekrarlanır):** canlı core belgeleri +
  canlı FM → `exit 2`; bayat belge + canlı FM → `EKSİK` 5 kalem; yeni belgeler + canlı FM →
  `16/16 [OK]`. Yöntem (ad-hoc, kalıcı betik YOK — makine yolu gömmemek için): geçici bir
  sandbox projeye FM kaynağının ilgili sürümünü koy, gate'i `--core <belge kökü>` +
  `CLAUDE_PROJECT_DIR=<sandbox>` ile çağır.
- ⚠ **Ad sözleşmesi:** gate adında **"freshness" GEÇMEZ** — `run_all_validators --quick`
  (pre-commit) o deseni atlar. Ad değişirse pre-commit'te sessizce ölür; regresyon çapası:
  `--quick` çıktısında gate satırının GÖRÜNMESİ (aynı koşuda "Playbook freshness" `[SKIP]`).

## B22 — `populate_tables.py` unit_kind kararı (CURR ↔ QUAN) + CSV kolon sözleşmesi
- Korpus: `python tests/fixtures/populate_tables_unit_kind/run.py` → **16 senaryo + 4 mutasyon**,
  exit 0. Suite içinden: `python tests/run_fixture_tests.py` (OZEL_TESTLER üyesi).
- Mutasyonlar korpusun **İÇİNDEDİR** (kaynak metni yamalanır; eski sürümü `git show` ile
  çekmeye gerek YOK) ve koşucu ayrıca **"yama tuttu mu"** kanıtı basar — yama bugünkü kaynağa
  uymazsa `sahte-yesil riski` ile exit 1 (mutasyonun sessizce NO-OP'a dönmesine karşı).
- ⚠ **Fixture'ın kendi dersi (iki tane):**
  1. `populate_tables` import anında `io.TextIOWrapper(sys.stdout.buffer)` kurar. Yalnız
     `sys.stdout`'u geri koymak **YETMEZ** — wrapper GC'ye girince sardığı GERÇEK buffer'ı
     KAPATIR ve sonraki `print` *"I/O operation on closed file"* ile patlar (ölçüldü). Korpus
     import sırasında stdout'u atılabilir bir `BytesIO`'ya bağlar.
  2. İkinci sinyal (referans DTEL) mutasyonu önce **KAÇIYORDU**: sinyal sökülünce sonuç yine
     `quantity` çıkar (varsayılan aynı yön) → annotation'a bakan çapa ayırt edemez. Ayırt edici
     **uyarı-İZİ**dir (çözüldüyse uyarı YOK, varsayılana düşüldüyse VAR) + yön-ikizi `S4b`
     (Z'li tutar DTEL'i + standart CUKY ref → currency).
- **ÜRETİCİ↔DENETÇİ mutabakatı:** DTEL sözlüğü `scripts/utils/ddic_semantics.py`'de TEK
  kaynaktır; `check_cds_currency_reference.py` de oradan import eder. Sözlüğe dokunulursa
  **İKİ** korpus koşulur: `populate_tables_unit_kind` + `cds_curr_satir_yorumu` (HARİTA
  ikisini de bağlar).
- ⚠ **Suite hijyeni (bu turun ürünü DEĞİL, gözlendi):** `run_fixture_tests.py` koşumu repo
  kökünde gitignored bir `.conn_adt` **BIRAKIR**; **ikinci ardışık koşumda**
  `conn_cift_anahtar`'ın "tier YOK → UNKNOWN" vektörü `tier=DEV` okuyup FAIL verir (123/124).
  Temiz ölçüm için koşumdan önce `rm -f .conn_adt`. Ayrı kuyruk kalemi.

## B23 — `infra_write_guard` (infra yüzeyine ana-oturum yazımı BLOK)
- Korpus: `python tests/fixtures/infra_write_guard/run.py` → **47/47**, exit 0. Suite içinden:
  `python tests/run_fixture_tests.py` (OZEL_TESTLER üyesi).
  ⚠ *(Bu blok 2026-08-29'a kadar **26/26 + 2 mutasyon** diyordu — BAYATTI. Kabuk kolu (kayıt #47)
  ve koşucu daraltması eklendiğinde sayı güncellenmemişti; rakam iki yerde yaşarsa biri bayatlar.)*
- **YEDİ mutasyon, yedisi de koşulur** (hiçbiri diğerini kapsamaz; herhangi biri tam puan
  verirse korpus o değişmez için BOŞTUR):
  `--mutasyon-blok` → **33/47** · `--mutasyon-cokme` → **35/48** (düşen: B10 + S4/S7/S9 kaba-ağ
  FP'si + koşucu sınıfı B11/B12/S12b + kabuk kolu; M1 vektörü `GUARD-COKTU` izini arar)
  `--mutasyon-bash-kol` → **42/47** · `--mutasyon-bash-cwd` → **46/47**
  **Koşucu daraltmasının ÜÇ parçası** (her biri TEK BAŞINA daraltmayı NO-OP yapar):
  `--mutasyon-kosucu-haric` → **44/47** (B11·B12·S12b) · `--mutasyon-kosucu-sinif` → **44/47**
  (AYNI üçü) · `--mutasyon-kosucu-proje` → **46/47** (YALNIZ B13; diğer ikisi onu DÜŞÜRMEZ).
- ⭐ **KOŞUCU ↔ KORPUS AYRIMI (2026-08-29 daraltması) — dokunmadan önce oku:** `_HARIC` fixture'ı
  tek parça sayıyordu. Artık **koşucu** (`tests/fixtures/<ad>/run.py` · `tests/run_*.py` · proje
  `scripts/validators-local/fixtures/**.py`) korunan sınıfta, **korpus** (`bad/`·`good/`·sahte
  ağaçlar) serbest. ⛔ **YALNIZ `_HARIC`'i daraltmak NO-OP'tur:** `_HARIC` tamamen kapatılınca
  `tests/` altındaki 139 dosyadan korunan sınıfa giren **1** tanedir ve o bir KORPUS dosyasıdır
  (`…/cekirdek_ikizi/scripts/mevcut.py`); 90 koşucunun hiçbiri yakalanmaz, çünkü `_KORUNAN_CORE`
  desenlerinin tamamı `^scripts/` ile başlar. Üç parça (istisna + core deseni + proje deseni)
  BİRLİKTE gerekir — `_ARACLAR`/Bash NO-OP tuzağının ikizi.
  **Gerçek-korpus ölçüm reçetesi (FP avı, fixture'dan ÖNCE koş):** `_HARIC`'i `re.compile(r"(?!x)x")`
  ile kapat, `tests/**` + proje `validators-local/**` üzerinde `_sinif()` çağır, koşucu/korpus
  ayrımını say. Beklenen: recall 92/92 (core) + 3/3 (proje), FP **0**.
  ⛔ `_KABA` (çökme ağı) BİLEREK genişletilmedi: alt-dizge testidir, `run.py` her projenin
  dosyasını yakalardı ⇒ çökme altında koşucu sınıfı serbest kalır (B10 ile aynı sınıf sınır).
  ⛔ **AÇIK KALEM:** kardeş `post_validate._INFRA_HARIC` (`:102`) hizalanmadı — nudge koşucuları
  hâlâ "infra değil" sayıyor (blok kolu yazımı zaten durdurduğu için canlıda etkisi ölçülmedi).
- Mutasyonlar **korpusun içinde** ve **bugünkü kaynaktan** üretilir (git ref'i YOK → "fix merge
  olunca taban kayar" tuzağı yapısal olarak yok). Desen tutmazsa koşucu **exit 3** verir ve
  **hiçbir sayı raporlamaz**.
- **Kimlik ayrımının kanıt tabanı** (guard'a dokunan HERKESİN bilmesi gereken tek şey): ana
  oturum payload'ında `agent_type`/`agent_id` **YOKTUR**, alt-ajanda **VARDIR**; `agent_type`
  ajan tanımının `name:`idir. Şema değişirse guard sessizce ya herkesi bloklar ya kimseyi —
  ölçüm reçetesi: sandbox proje + `.claude/settings.json`'a stdin'i dosyaya döken bir
  PreToolUse hook'u + `claude -p "... Task ile <ajan-tipi> alt-ajanı Write yapsın"`.
- ⚠ **Korpusun kendi dersleri:** (1) `--mutasyon-cokme`de S4/S7/S9'un düşmesi **kusur değil**,
  fail-closed degrade'in fiyatıdır — kaba ağ marker/istisna okumaz. (2) **B10 çökmede kaçar**
  (`scripts/**/*.py` sınıfı kaba ağda yok); kaba ağı genişletmek her projenin `scripts/*.py`'ını
  bloklardı ⇒ bilinçli sınır. (3) K4 bugün **exit 1** ölçüyor = kopuk junction'da guard devre
  dışı (`hook_shim._FAIL_CLOSED` üyesi değil); vektör `{1,2}` kabul eder, böylece lider bu
  kararı verdiğinde test kırılmaz, yalnız etiketi değişir.
- **Dokunulursa BİRLİKTE koşulacaklar:** `negatif_test_harness` (V13/V16 sınıf kaydı) ·
  `fs_docstd` (aynı yüzeydeki `post_validate` infra-express nudge'ı) · `run_guard_fixture_tests`
  (aynı matcher'daki `pre_tool_guard`).

## B24 — `check_cds_currency_reference` KAYNAK-TİPİ tespiti + çıkış-kodu sözleşmesi
- Korpus: `python tests/fixtures/cds_curr_kaynak_tipi/run.py` → **19/19**, exit 0.
  Mutasyon: `... run.py --mutasyon` → **4/4 ayırt edici**. Suite içinden:
  `python tests/run_fixture_tests.py` (OZEL_TESTLER üyesi; HARİTA satırı validator'a bağlı).
- **ÇIKIŞ-KODU SÖZLEŞMESİ (bu turda yazıldı, tüketicisi `run_review` rc!=0 → FAIL):**
  `0` = DENETLENDİ, BLOCKER yok (WARNING olabilir) veya table-function bilinçli atlandı ·
  `1` = DENETLENDİ, en az 1 BLOCKER · `2` = **ÖLÇÜLEMEDİ** (dosya yok VEYA kaynak tipi
  tespit edilemedi). rc=0 ile "bakmadım"ı ifade etmek YASAK — kusurun kendisi buydu.
- **Korpus CLI üzerinden (subprocess) ölçer**, fonksiyon import ederek DEĞİL: ölçülmek
  istenen değişmez `run_review`'in gördüğü ÇIKIŞ KODU'dur; `main()`'deki dallanma
  fonksiyon-seviyesi testte görünmez.
- ⚠ **Mutant nerede yaşar:** kopya **gerçek `scripts/validators/` dizinine**
  `_mutant_*.py` adıyla yazılır (finally'de silinir). Validator kendi yolundan
  `parents[1]` ile `utils.ddic_semantics`'i import eder → tempdir'e kopyalanırsa import
  ÖLÜR, her mutasyon "yakalandı" görünür (SAHTE-KIRMIZI).
- **İki değişmez → iki mutasyon** (M3/M4 ek kapılar): `M1` eski alt-dizi mantığı geri →
  A-vektörleri düşer · `M2` fail-open (rc=2 yerine 0) → B1/B2/B3 düşer · `M3` abstract
  entity 'table' yoluna → A4 düşer (FP kapısı) · `M4` TF atlaması sökülü → C5 düşer.
- ⚠ **Kill edilemeyen aday, bilerek yazılmadı:** tespit fonksiyonundaki `yorumu_kirp`
  çağrısı savunmacıdır ama ÖLÇÜLEBİLİR etkisi yok (`// define view` satırı zaten
  `^\s*define` anchor'ına uymaz) → onun için mutasyon UYDURULMADI.
- **Dokunulursa BİRLİKTE koşulacaklar:** `cds_curr_satir_yorumu` (V1, aynı denetçi) ·
  `populate_tables_unit_kind` (B-13, aynı DTEL sözlüğü) — HARİTA üçünü de bağlar.
- **Gerçek-korpus regresyon reçetesi (tüketici projede):** validator'ı `<source_root>`
  altındaki tüm `*.cds|*.asddls|*.ddl|*.ddls` dosyalarına koş, rc dağılımını fix ÖNCESİ
  sürümle karşılaştır. Beklenen: yalnız daha önce "tespit edilemedi" diyen dosyaların
  çıktısı değişir, geri kalan **BAYT AYNI** kalır.

## B25 — PARTİ-1 "sessiz veri bozan" dörtlüsü (msgtext guard · aktivasyon notu · çıktı dürüstlüğü)
- Üç korpus, hepsi OZEL_TESTLER üyesi (suite içinden de koşar):
  `python tests/fixtures/msgtext_uzunluk_guard/run.py`     → **8 senaryo + 3 mutasyon**, exit 0
  `python tests/fixtures/ddic_aktivasyon_notu/run.py`      → **9 senaryo + 4 mutasyon**, exit 0
  `python tests/fixtures/cikti_iddiasi_durustlugu/run.py`  → **9 senaryo + 3 mutasyon**, exit 0
  Tam suite: `python tests/run_fixture_tests.py` → **130/130** (⚠ önce `rm -f .conn_adt`, bkz. B22 notu).
- **Mutasyonlar korpusun İÇİNDEDİR** ve BUGÜNKÜ kaynaktan üretilir (git ref'i YOK ⇒ "fix
  merge olunca taban kayar" tuzağı yapısal olarak yok). Her koşucu ayrıca **"yama tuttu mu"**
  kanıtı basar; yama bugünkü kaynağa uymazsa sahte-yeşil yerine FAIL verir.
- ⚠ **stdout gaspı (B22'nin dersi, burada da geçerli):** `populate_message_class`,
  `run_pretty_printer` ve `sap_sync_pull` import anında `io.TextIOWrapper(sys.stdout.buffer)`
  kurar. Yalnız `sys.stdout`'u geri koymak YETMEZ — wrapper GC'ye girince sardığı GERÇEK
  buffer'ı KAPATIR. Üç korpus da import sırasında stdout'u **atılabilir bir BytesIO**'ya
  bağlar ve wrapper'lara referans tutar (`_mod_refs`). Bu satırlar SİLİNMEZ.
- ⭐ **METİN ARAMASI İKİ KEZ YANILDI — çapalar AST'dir, `in` değil** (ilk koşumda ikisi de
  gerçekleşti, kayıt dürüstlük için):
  ① `"push_object" in src` → `run_pretty_printer` **docstring'inde** *"push_object.py ile yaz"*
     yazdığı için "YAZMA çağrısı var" sandı (sahte-KIRMIZI). Çözüm: `ast` ile GERÇEK `Call`
     adları toplanır; yorum/docstring/dize sayılmaz.
  ② `"_alt_include_uyar(obj" in src` → fonksiyonun kendi **`def` satırıyla** eşleşti ve çağrı
     sökülmüş olsa bile True döndü ⇒ **M2 mutasyonu KAÇTI**. Çözüm: `_kablolu_mu()` — `main`
     gövdesinde `ast.Call` arar. **Çağrı ile TANIM metinde birbirine benzer; AST ayırır.**
- **Değişmez ↔ mutasyon eşlemesi** (biri diğerini KAPSAMAZ; herhangi biri tam puan verirse
  korpus o değişmez için BOŞTUR):
  `msgtext`: M1 guard'ı sök (tespit) · M2 yalnız İLK ihlali raporla (tamlık) · M3 eşik 73→200 (değer)
  `aktivasyon`: M1 boş listede de bas (gürültü) · M2 geçersiz `--type` (üretici↔tüketici) ·
                M3 çağrıyı sök (kablolama) · M4 non-ASCII geri koy (C-ENC-01)
  `çıktı`: M1 `applied to` geri (iddia) · M2 uyarıyı sök (sessizlik) · M3 marker'ı yerel
           kopyaya çevir (tek-kaynak)
- ⭐ **ÜRETİCİ↔TÜKETİCİ vektörü (S3, `ddic_aktivasyon_notu`):** notun bastığı `--type` değeri
  `activate_object.py`'nin argparse `choices`'ından **canlı çözülür** (`object_types`
  import edilir), metin kıyası YAPILMAZ. `list_supported_types()`/`OBJECT_TYPE_ALIASES`
  değişirse bu vektör kırılır — istenen davranış: notun bastığı komut geçersizleşmesin.
- **FP çapaları (ayırt edicilerle AYNI vektöre konmaz):** `msgtext` S2/S3/S5/S6/S8 ·
  `aktivasyon` S2 (boş liste sessiz) · `çıktı` B2 (alt-include yoksa sessiz) + B1 içindeki
  komşu-sınıf çapası (`ZCL_BASKA.ccimp.abap` uyarıya KARIŞMAMALI).
- **Dokunulursa BİRLİKTE koşulacaklar:** `populate_tables.py`'ye dokunan her tur
  `populate_tables_unit_kind` (B22) **ve** `ddic_aktivasyon_notu`'nu koşar (HARİTA ikisini de
  bağlar). `source_drift.py`'ye dokunan tur `cikti_iddiasi_durustlugu`'nu koşar
  (`_CLASS_SUBSOURCE_MARKERS` oradan import edilir).
- ⚠ **DOĞRULANAMADI (canlı):** dördü de SAP'ye karşı koşulmadı — fixture'lar SAP'yi taklit
  eder / sahte client kullanır. İlk gerçek kullanımda doğrulanacak: ① uzun metinli CSV'de
  fail-closed'ın CSRF/LOCK/PUT'a **hiç gitmediği** ② `populate_*` kapanış notunun gerçek
  koşumda göründüğü ve komutun **çalıştığı** ③ `run_pretty_printer`'ın yeni metinleri.

## B26 — PARTİ-2 "sahte yeşil" dörtlüsü (cds-derinlik · transport-sıfır · pre-commit · süit hijyeni)
- Dört korpus (hepsi OZEL_TESTLER üyesi):
  `python tests/fixtures/cds_curr_eksik_annotation/run.py`      → **9 senaryo + 5 mutasyon**, exit 0
  `python tests/fixtures/transport_sifir_kaniti/run.py`         → **7 senaryo + 3 mutasyon**, exit 0
  `python tests/fixtures/precommit_junction_failclosed/run.py`  → **4 senaryo + 2 mutasyon**, exit 0
  `python tests/fixtures/suite_ortam_hijyeni/run.py`            → **5 senaryo + 3 mutasyon**, exit 0
  Tam suite: `python tests/run_fixture_tests.py` → **134/134**.
- ⭐ **İDEMPOTANS ARTIK KORPUS-DIŞI BİR ADIMDIR (elle koş, B22'nin açık kalemi buydu):**
  süiti **arka arkaya İKİ KEZ** koş; ikisi de **134/134** vermeli. Ölçüldü 2026-08-20:
  fix ÖNCESİ 130 → **129** (`conn_cift_anahtar` SAPMA), fix SONRASI 134 → **134**.
  Korpusa konmadı çünkü iki tam koşum ≈ 6 dk; `suite_ortam_hijyeni` bunun yerine
  hijyen fonksiyonlarını + AST kablolamasını ölçer.
- ⚠ **KİRLİ ORTAM SONDASI:** repo kökünde koşumdan ÖNCE `.conn_adt` varsa süit artık
  **görünür uyarı** basar. O uyarıyı gördüğünde sonucu KANIT SAYMA — `rm -f .conn_adt`
  ile temiz ölçüm al. ⛔ Süit, koşum öncesi VAR OLAN dosyayı **SİLMEZ** (kullanıcınındır);
  yalnız kendi ürettiğini siler. `suite_ortam_hijyeni` S4 tam bunu çivilliyor.
- ⚠ **`cds_curr_eksik_annotation` MUTANTI GERÇEK `scripts/validators/` DİZİNİNDE yaşar**
  (`_mutant_cds_curr.py`, finally'de silinir) — B24'ün dersi: validator kendi yolundan
  `parents[1]` ile `utils.ddic_semantics`'i import eder; tempdir'e kopyalanırsa import
  ÖLÜR ve HER mutasyon "yakalandı" görünür (SAHTE-KIRMIZI).
- ⚠ **`transport_sifir_kaniti` iki tuzağı belgeler (ikisi de bu turda YAŞANDI):**
  ① Mutasyon için TÜM modülü `exec` ETME — modül-seviyesi yan etkiler
     `SAPConnectionError` fırlatır ve koşucu bunu *"mutasyon YAKALANDI"* sayar
     (**çökme ≠ FAIL**; üç mutasyonun üçü de böyle sahte-yeşil verdi). Çözüm: AST ile
     yalnız fonksiyon bloğunu ayıkla, **dekoratörü ATLA** (`@profil_tool` profil
     çözümü `.conn_adt`ye gider), globals olarak gerçek modülün namespace'ini ver.
  ② Sahte client stub'ı **fonksiyonun KENDİ globals'ına** uygulanmalı; yalnız
     `query` modülüne uygulanırsa mutant globals KOPYASINDAKİ gerçek `_get_client`i
     görür ve GERÇEK SAP bağlantısı dener.
- ⚠ **`precommit_junction_failclosed` GERÇEK git deposu + GERÇEK kabuk kullanır:**
  şablon `git rev-parse --show-toplevel` çağırır; sahte dizin sessizce BAŞKA bir ağacı
  gösterirdi ("kod ≠ kablolama"nın kabuk yüzü). `sh` yoksa korpus **exit 1** verir
  (sessiz geçme YOK).
- ⭐ **Metin çapası İKİ KEZ daha yanıldı (Parti-1'deki dersin nüksü) — çapa AST'dir:**
  `_alt_include_uyar(` ve `_ortam_hijyeni_bitir(` gibi adlar fonksiyonun kendi `def`
  satırıyla eşleşir; ayrıca docstring'de TARİHÇE olarak alıntılanan çürütülmüş cümle
  "hâlâ öğretiyor" sanılır. ⇒ Çürütülmüş cümle `query.py` docstring'inde **bilerek
  yeniden yazılmıyor** ve kablolama soruları AST ile sorulur.
- **Dokunulursa BİRLİKTE koşulacaklar:** `check_cds_currency_reference.py`'ye dokunan
  tur **dört** korpus koşar: `cds_curr_satir_yorumu` (V1) · `cds_curr_kaynak_tipi` (V2,
  `--mutasyon` dahil) · `populate_tables_unit_kind` (B-13, aynı sözlük) ·
  `cds_curr_eksik_annotation` (derinlik). HARİTA dördünü de bağlar.
- **GERÇEK-KORPUS REGRESYON REÇETESİ (①):** validator'ı `<source_root>` altındaki tüm
  `*.cds` dosyalarına ESKİ ve YENİ sürümle koş, **rc dağılımını** karşılaştır.
  Beklenen: rc dağılımı **DEĞİŞMEZ** (WARNING build'i durdurmaz), yalnız
  `C-CDS-CUR/QUAN-05` satırları eklenir. Ölçüldü: 233 dosya · rc değişen **0** ·
  yeni bulgu **46**.
- ⚠ **DOĞRULANAMADI (canlı):** ② SAP'ye karşı koşulmadı. Sahte-sıfırın KÖK SEBEBİ
  (araç hangi sorguyu koşuyor da `E070`'i ıskalıyor) **gateway'in canlı ölçümüdür**;
  bu tur yalnız SÖZLEŞMEYİ düzeltti. ③ gerçek bir projede junction kırıp commit
  denemesiyle bir kez teyit edilmeli (fixture sentetik depo kullanır).

## B27 — PARTİ-2b şablon + manifest üçlüsü (.rules.md.tmpl · spawn-brief/lint · behavior_manifest)
- İki korpus (ikisi de OZEL_TESTLER üyesi):
  `python tests/fixtures/sablon_zorunlu_maddeler/run.py` → **11 senaryo + 5 mutasyon**, exit 0
    ⚠ *güncellendi 2026-08-29:* A4/A5 + M4/M5 `6e4a1ec`'te eklenmişti, reçete o gün güncellenmemişti
    (9+3 yazıyordu — bayat iddia). A4/A5 çapası aynı gün **`Class` eksenine taşındı**: dayandığı
    Message Class çelişkisi kapandı, `Class` çelişkisi (`ZCL_{PKG}_*` ↔ canlı kısaltılmış biçim `ZCL_<PKG#>_*`) açık kaldı.
  `python tests/fixtures/manifest_secici_onay/run.py`    → **9 senaryo + 4 mutasyon**, exit 0
  Dokunulan hook regresyonu: `python tests/fixtures/prior_art_kb01/run.py` → **17/17**.
  Tam suite: `python tests/run_fixture_tests.py` → **136/136**.
- ⭐ **ÖNEKLER KORPUSTA KOPYALANMAZ:** `sablon_zorunlu_maddeler` DDIC öneklerini
  `standards/01-naming.md` **§4.4.5 tablosundan OKUR**. İkinci bir kopya tutulsaydı
  bayatlar ve korpus standardı değil **kendi ezberini** doğrulardı. Standardın tablo
  biçimi değişirse `_std_ddic_onekleri()` boş döner → A1 kırmızı (fail-loud, sessiz
  geçme yok).
- ⚠ **Şablon mutasyonu DİSKE yazılır** (`.rules.md.tmpl` geçici olarak yamalanır) ve
  `finally` ile geri alınır; koşucu ayrıca **kalıntı kontrolü** basar. Mutasyon artığı
  kalırsa süit FAIL verir — çünkü kalıntı bir sonraki koşumda **sessiz bozulma** olurdu.
- ⭐ **`brifing-lint` yeni ekseni DAR — genişletmeden ÖNCE TABANI ÖLÇ.** Ölçüm
  (587 gerçek brif, transcript korpusu, `utils.claude_paths.transcript_dizini`):
  | Eksen | Ateşleme |
  |---|---|
  | ham *"ENGELLENIRSEN maddesi var mı?"* | **%86,7** ⇒ KULLANILAMAZ (uyarı körlüğü) |
  | **DAR** (başka-ağaç **+** yazma işi, madde yok) | **%16,0** (kapsam %18,4) |
  | mevcut `GOREV` ekseni (kıyas tabanı) | %25,0 |
  | KB-01 ekseninin ölçülmüş gürültü tabanı | %13,9 |
  | ⛔ `T3-KİMLİK` (2026-08-21, **GERİ ALINDI aynı gün**) | %4,8 — *bant altı* ama **precision 0** |
  | ⛔ `DEPLOY` (2026-08-21, **GERİ ALINDI aynı gün**) | %5,3 — *bant altı* ama **precision 0** |

  ⛔⛔ **BU TABLONUN KENDİSİ YANILTTI — son iki satır o yüzden burada.** Tablo yalnız
  *ateşleme* ölçüyor; 2026-08-21'de iki eksen bu tabloya bakılarak (*"%4,8 ve %5,3, bant
  altı ✅"*) kabul edildi ve **isabetleri sıfır** olduğu için aynı gün geri alındı (609
  gerçek brif: `T3-KİMLİK` 30 ateşlemenin 30'u salt-okur; `DEPLOY` 32 ateşlemenin 0'ı
  gerçek deploy işi). **Düşük ateşleme, doğru ateşleme demek değildir** — bir eksen
  ancak ateşleme **<%13,9** *ve* precision **≥%70** *ve* recall **≥%50** ile kabul edilir.
  Alet: `governance/research/brifing-lint-olcum-2026-08-21/precision_harness.py`.
  Kaldırma kaydı: `governance/removed-controls.md` (B8 bölümündeki ders bloğu da oku).
  ⛔ Ekseni gevşetmek (ör. `yazma` şartını kaldırmak) korpusta **M3 mutasyonudur** ve
  B3 (yalnız-okuma FP çapası) onu kırar.
- ⭐⭐ **`ŞABLON` ekseni GERÇEK POZİTİFTİR — oranına bakıp GEVŞETME (ölçüm 2026-08-21).**
  Tüm korpusta ateşleme **%55,5** görünür ve bu, yukarıdaki bandın (**<%13,9**) çok
  üstünde olduğu için *"gürültülü eksen, gevşetelim"* diye okunmaya AÇIKTIR. **Yanlış
  okumadır.** Kontrol grubu: aynı gün öğleden sonra R2 şablonu **tam doldurulan 3 brifin
  3'ünde de ateşleme %0,0**. Yani eksen gürültü üretmiyor — **başlıksız brifi doğru
  işaretliyor**; yüksek oran korpusun çoğunun şablonsuz yazılmış olmasından geliyor,
  eksenin isabetsizliğinden değil.
  📌 Kabul ölçütü **üç ayaklıdır** (ateşleme · precision · recall); bir eksen yalnız
  ateşleme oranına bakılarak ne kabul edilir ne reddedilir. Yukarıdaki iki ⛔ satırı
  *düşük oranın* yanılttığı vakadır; bu satır *yüksek oranın* yanıltabileceği ters
  vakadır. **İkisinin dersi aynı: oran tek başına karar vermez.**
  ⛔ Bu ekseni gevşetmek, 2026-08-21'de geri aldığımız hatanın **tersten tekrarı** olur.
- ⚠⚠ **`behavior_manifest`te İKİ GEVŞETME var — dokunmadan önce POZİTİF KONTROLLERİ oku:**
  (a) `worktrees` prune'da → FP çapası **S1**, pozitif kontrol **S2** (ana ağaçtaki gerçek
      nested `CLAUDE.md` hâlâ taranır).
  (b) `_hash` satır-sonunu normalize eder → FP çapası **S3**, pozitif kontrol **S4**
      (**tek karakterlik** gerçek değişiklik hâlâ yakalanır).
  ⛔ S2/S4 **SİLİNMEZ**: onlar olmadan iki gevşetmenin "kapıyı körletmediği" iddiası
  kanıtsız kalır. Mutasyonlar M1/M2 tam da bu iki değişmezi sınar.
- **`--only` sözleşmesi:** `generate --only <yol>` / `--only a,b` / tekrarlı `--only`.
  Fail-closed iki dal: bilinmeyen yol → `SystemExit` · manifest yokken `--only` →
  `SystemExit` (önce tam `generate`). ⛔ `verify` ile `generate` **tek** kıyas fonksiyonu
  (`_sapmalar`) kullanır — ayrışan iki kıyas mantığı bu evde daha önce kusur üretti.
- ⓘ `behavior-manifest.json` **gitignore'dadır** (makine-lokal) ⇒ değişikliği PR'da kimse
  göremez. Tek denetim yüzeyi `generate`in ÇIKTISIDIR; bu yüzden "ONAYLANAN / BEKLEMEDE"
  listeleri ve TOPLU ONAY uyarısı **çözümün parçasıdır**, kozmetik değil (S7 + M4).
- ⚠ **DOĞRULANAMADI:** yeni lint ekseninin **canlı bir spawn'da** ateşlediği ölçülmedi
  (hook kablolaması oturum başında yüklenir); kanıt sentetik payload + gerçek
  `_brifing_lint` fonksiyonudur. İlk gerçek spawn'da teyit et.
- ⚠ **AÇIK (bu turda dokunulmadı):** şablonun **Message Class** satırı üç kaynakta üç
  farklı (standart `MC` · şablon çıplak `{PKG}` · gerçek kullanım `{PKG}_MSG`) ve
  **Search Help** satırı hiç yok. İkisi de **kural kararıdır (K4)**, mekanik fix değil.

## B28 — PARTİ-3 iki GEVŞETME (itg_signoff biçim toleransı · worktree dışlama)
```bash
python tests/fixtures/gevsetme_pozitif_kontrol/run.py   # 11 senaryo + 5 mutasyon, exit 0
python tests/fixtures/itg_alan_dolulugu/run.py          # 11/11  (2026-08-01 sıkılaştırması)
python tests/fixtures/fs_docstd/run.py                  # 38/38  + 9 mutasyon (B9b)
python tests/run_fixture_tests.py                       # 137/137
```
- ⛔⛔ **BU KORPUSTA SİLİNEMEZ VEKTÖRLER VAR.** İki gevşetme **kullanıcı onaylı** ve onay
  *"kapıyı körletmediğini KANITLA"* şartıyla alındı. Kanıt şunlardır:
  | Vektör | Ne kanıtlar |
  |---|---|
  | **A2** boş şablon + `MUTABAKAT:[x]` → BLOCKER | doluluk denetimi ayakta |
  | **A3** tolere edilen başlık ama **BÖLÜM BOŞ** → BLOCKER | tolerans doluluğu yemedi |
  | **A4** prior-art **düzyazı** (referans izi yok) → BLOCKER | arama zorunluluğu ayakta |
  | **B2** ana ağaçtaki **gerçek** ihlal yakalanır | dışlama dedektörü öldürmedi |
  Bunlardan biri silinirse ilgili gevşetme **kanıtsız** kalır — geri al ya da yeniden kanıtla.
- ⭐ **SINIR MUTASYONU M3** (`_dolu_mu` hep `True`) korpusun en önemli vektörüdür: doluluk
  zinciri sökülünce **A3 kırmızı** olmalı. Yeşil kalırsa tolerans doluluğu yemiş demektir.
- **TOLERANSIN SINIRI ÖLÇÜLÜDÜR:** `_ARA = r"[^\n:]{0,24}"` — satır-sonu ve `:` dışlanır,
  en fazla 24 karakter. Sınırsız `.*` iki AYRI alanın başlığını birbirine bağlar ve **alan
  karışması** üretir. **A7** bu sınırı denetler ⇒ genişletmek isteyen A7'yi güncellemek
  ZORUNDA (sessizce genişletilemez).
- ⚠ **`check_itg_signoff`te İKİ DEĞER-ÇIKARMA BİÇİMİ var** (`_ALAN_BASLIK` = `Alan: değer`
  satırı · `_ALAN_MD_BASLIK` = markdown bölüm başlığı). ⛔ Markdown biçiminde **başlık
  satırının kendisi değere DAHİL EDİLMEZ** — edilseydi boş bir bölüm bile "dolu" görünürdü
  ve doluluk denetimi **sessizce ölürdü**. A3 tam bunu ölçer.
- ⚠ **Mutant GERÇEK `scripts/validators/` dizininde yaşar** (`_mutant_itg.py`, `finally`de
  silinir) — B24 dersi: validator kendi yolundan komşu modülleri çözer; tempdir'e
  kopyalanırsa import ölür ve HER mutasyon "yakalandı" görünür (SAHTE-KIRMIZI).
- ⭐ **WALK-PRUNE SINIFINI ADA GÖRE ARAMA.** Aynı küme repoda **üç farklı adla** sekiz
  validator'da yaşıyor: `_SKIP_SEGMENTS` ×4 · `_SKIP` ×1 · `_prune` ×3 (+ `behavior_manifest`
  yerel `prune`). `rg _SKIP_SEGMENTS` sınıfın **yarısını ıskalar** — doğru arama
  `rg "dirnames\[:\]"`. **B4** vektörü bu taramayı ad-bağımsız yapar ve yeni bir walk-pruner
  eklenip `worktrees` unutulursa kırılır.
  ⛔ Kümeleri TEK kümede birleştirme AYRI bir karardır: bilinçli olarak farklılar
  (ui5 dar · fs_docstd `archive` taşır).
- ⚠ **DOĞRULANAMADI:** worktree çiftlenmesi (ölçülmüş 87→174) bugün **canlı repro
  edilemedi** — projede şu an **sıfır** worktree var. FP sentetik ağaçla yeniden üretildi
  (B1) ve M4/M5 onu geri getirdi. Gerçek ortamda ilk worktree açıldığında sayının
  tekilleştiği bir kez teyit edilmeli.
- **Dokunulursa BİRLİKTE koşulacaklar:** `check_itg_signoff.py` → `itg_alan_dolulugu`
  **VE** `gevsetme_pozitif_kontrol` (biri doluluğu, öteki toleransı ölçer; HARİTA ikisini
  de bağlar). `check_fs_no_analysis_log.py` → `fs_docstd` (9 mutasyonuyla) **VE**
  `gevsetme_pozitif_kontrol`.

## B29 — PARTİ-4 son parti (kapsam paydası · kök izolasyonu · JSON kaçışı · kum sızıntısı · offline MCP · SAP'siz ui-smoke · Bash tetiği)
- Yedi korpus (hepsi OZEL_TESTLER üyesi), tek tek koşum:
  `python tests/fixtures/validator_kapsam_paydasi/run.py`        → **31 senaryo + 4 mutasyon**, exit 0
  `python tests/fixtures/console_utf8_kok_izolasyonu/run.py`     → **7 + 3**, exit 0
  `python tests/fixtures/yabanci_proje_json_kacisi/run.py`       → **10 + 4**, exit 0
  `python tests/fixtures/conn_kum_sizintisi/run.py`              → **7 + 4**, exit 0
  `python tests/fixtures/mcp_profil_aktivasyon_offline/run.py`   → **15 + 4**, exit 0
  `python tests/fixtures/ui_smoke_sapsiz/run.py`                 → **8 + 3**, exit 0
  `python tests/fixtures/hook_bash_ve_stderr_kapsami/run.py`     → **9 + 4**, exit 0
  Tam süit: `python tests/run_fixture_tests.py` → **144/144**, **İKİ ARDIŞIK KOŞUM AYNI**
  (⚠ süit sayısı bugün **145/145** — B30 ile `byassoc_advisory` korpusu eklendi; bu
  korpusun kendi sayısı **9 + 4** olarak DEĞİŞMEDİ, A3 yeniden kuruldu ama bölünmedi.)

- ⛔⛔ **PLATFORM, DEĞİŞKENİ GİZLİCE İKİLEŞTİRİR — `[YAKALANDI]` Windows'ta, `[KACTI]`
  Linux'ta (ölçüldü 2026-08-20, `DEV_CORE#150` CI kırmızısı).** Bir korpus Bash payload'ına
  yolu `str(Path)` ile gömerse Windows'ta komut metni `C:\…\docs\KD-X.md` olur. Tüketicinin
  yol-çıkarımı `/` üzerinden çalışır (normalizasyon hook'un İÇİNDEDİR, komut metninde
  değil) ⇒ ters-bölü, çıkarımı **son bileşende keser**. Sonuç: mutasyon Windows'ta
  **yanlış sebeple** yakalanır, Linux'ta kaçar. ⇒ **Kural: Bash `command` metnindeki yol
  DAİMA `Path.as_posix()`; `file_path` payload'ında NATIVE (`str`) — ikisi ayrı yüzeydir.**
  Yapısal koruma: `_bash()` yardımcı fonksiyonu ters-bölülü komutu `AssertionError` ile
  REDDEDER (regresyon Windows'ta gürültülü çöker, sessiz platform-sapması olmaz).
  ⭐ **Yerelde Linux yoksa repro böyle yapılır** (WSL/Docker gerekmez): vektörün yolunu
  `as_posix()`e çevir — bu, regex/eşleme açısından Linux'un gördüğü metnin birebir aynısıdır
  (`C:` öneki hiçbir desende eşleşmez). Ölçüldü: aynı mutasyonda `str` → nudge YOK,
  `as_posix()` → nudge VAR.

- ⛔⛔ **MUTASYON GERÇEK KAYNAĞA YAZILMAZ — bu turda ÜRETİLEN ve yakalanan kirlenme:**
  İlk sürümde dört korpus mutasyonu gerçek dosyaya yazıp `finally`de geri alıyordu.
  Art arda koşumlarda kalıntı BİRİKTİ; bir noktada `_profile.py` **fail-closed enum
  doğrulaması SÖKÜLMÜŞ** hâlde diskte kaldı ve komşu korpus `fs_docstd` bu kalıntıyı
  gerçek ihlal sanıp FAIL verdi (süit 143→142, idempotans kırık). ⇒ Üç güvenli desen:
    ① **izole ağaç kopyası** — import zinciri gerektiğinde (`utils.*` `parents[1]`den
       çözülür): `shutil.copytree` ile `scripts/` (+ gerekirse `mcp_servers/`) kopyala,
       mutasyonu KOPYAYA yaz, tüketiciyi kopyadan koş. ⚠ Yalnız mutasyona uğrayan
       dosyayı kopyalamak YETMEZ: import ÖLÜR ve **her mutasyon "yakalandı" görünür**.
    ② **kardeş `_mutant_*.py`** — tüketici dosyayı YOLDAN alıyorsa (hook, script).
       Aynı dizinde durmalı ki `parents[N]` derinliği ve komşu import'lar değişmesin.
    ③ **bellekte `exec`** — mutasyona uğrayan şey KOŞMAKTA OLAN koşucunun kendisiyse
       (`run_fixture_tests.py`): diske yazmak koşan süiti bozar.
  ⭐ **Her korpusa `F1 İZOLASYON` vektörü ZORUNLU:** koşum sonunda gerçek dosyaların
  hash'i başlangıçtakiyle AYNI olmalı **ve** kardeş mutant dosya KALMAMIŞ olmalı.
  Bu bir "temizlik kontrolü" değil, korpusun kendi DEĞİŞMEZİdir.

- ⭐ **BOŞ-SANDBOX SONDASI (K1'in ölçüm yöntemi — yeniden kullanılabilir):** bir
  validator ailesinin *"yeşilinin paydası"* şöyle ölçülür: `project.yaml` + BOŞ
  `SOURCE_CODES/` içeren geçici bir proje kur, `CLAUDE_PROJECT_DIR`i oraya çevir,
  aileyi koş. `[OK]/temiz` diyen ama dosya sayısı basmayan her üye **sessiz kapsam
  kaybı** adayıdır. Kontrol grubu ŞART: aynı üyeler DOLU sandbox'ta ihlali yakalamalı
  (yakalamıyorsa sorun görünürlük değil, dedektördür).
  ⚠ **Regex ile "sayı basıyor mu" ARAMA** — bu turda ilk deneme `rg "(taran|scanned)"`
  idi ve kelime parçalarına takılıp yanlış sınıf verdi. **Davranışı koş, çıktıyı oku.**

- ⛔ **K1 SINIRI (silinemez):** `n==0` **FAIL ÜRETMEZ**. `validator_kapsam_paydasi`
  **X1** bunu ölçer (boş sandbox'ta 12'sinin de çıkış kodu 0) ve **M3** ("0 dosyayı
  FAIL yap") onu kırmızı yakar. Sıfır kapsam MEŞRU olabilir; sertleştirme AYRI bir
  karardır (ADR 0019 + gate-moratoryumu).

- ⛔ **K8② SINIRI (silinemez):** kapsam genişlemesinin pozitif kontrolü **M4**'tür —
  bir nudge'a çıplak `playbook/...md` konur ve gate'in **FAIL** vermesi beklenir.
  Yol sayısının artması (4→8) *"yakalıyor"* demek DEĞİLDİR.

- ⚠ **"Koştu mu" sorusu ÇIKTI METNİYLE cevaplanmaz (K7 dersi):** `[DUR]` görmek
  playwright'ın koşmadığını KANITLAMAZ (mesaj basılıp yine koşulabilirdi). PATH'e
  sahte bir `npx` kabuğu konur, kabuk bir **İZ DOSYASI** yazar; ölçüt o dosyanın
  varlığıdır. Aynı desen "gerçekten alt-süreç başlattı mı" sorularının hepsinde geçerli.

- ⚠ **DEDUP MARKER'LI nudge'ı ölçerken TEMİZ kök kullan (K8② dersi):** `post_validate`
  doc-fs nudge'ı bir OKU-işaretçisi tutar; gerçek proje kökünde yoklarsan sonuç GÜNE
  göre değişir (bugün 4 yol, yarın 0) ve gate **sessizce boşalır**. `_stderr_ciktisi`
  her çağrıda taze sandbox kurar; `B2` vektörü ardışık iki koşumun AYNI toplamı
  vermesini çivilendirir.

- ⚠ **ÖLÜ VEKTÖR TUZAĞI (K4'te yaşandı):** savunma derinliği varken tek katmanı söken
  mutasyon ISKALAR; `P1` (veri kaybı olmaz) hiçbir mutasyonla kırılamıyordu ⇒ pratikte
  **hiç düşmeyen bir yeşil**di. Çözüm `M4`: ÜÇ katmanı (explicit-dir · PWD temizliği ·
  KUM-DIŞI çapası) BİRDEN sök → P1 kırmızı. **Kural: her ⭐ vektörün onu kıran EN AZ
  BİR mutasyonu olmalı; yoksa vektör dekordur.**

- ⚠ **Çapayı YANLIŞ ŞEYE bağlama (K8'de yaşandı):** A2 önce bir FS dokümanıyla
  yazıldı ve FAIL verdi — sebep ölçülen şey (Bash yol çıkarımı) değil, o yolun FS
  nudge'ını hiç tetiklememesiydi. Nudge'ı ATEŞLEDİĞİ BİLİNEN bir doküman tipi seçilerek
  değişken tek başına bırakıldı. Aynı sınıf K6/A2'de de çıktı (segment çok parçalı
  olduğu için `/` SAYMAK yanıltıcıydı → tam eşitlik).

- **Dokunulursa BİRLİKTE koşulacaklar:** `kapsam.py`ye ya da 12 validator'dan birine
  dokunan tur `validator_kapsam_paydasi` + o validator'ın `V:` çiftini koşar (HARİTA
  bağladı). `run_fixture_tests.py` hijyen fonksiyonlarına dokunan tur **hem**
  `suite_ortam_hijyeni` **hem** `conn_kum_sizintisi` koşar (imza sözleşmesi ikisinde
  de tüketiliyor — bu turda imza `bool`→demet olunca `suite_ortam_hijyeni` ÇÖKTÜ;
  ters-yön kontrolü olmasaydı sessiz kalırdı).

- ⛔ **KORPUS CI'DA KOŞACAK MI? — `mcp` TUZAĞI (K6'da yakalandı):** `atom.py` modül
  seviyesinde `_app`i, o da `mcp.server.fastmcp`i çeker. **CI'da `mcp` KURULU DEĞİL**
  (`core-ci.yml` yalnız `requests urllib3 python-dotenv` kurar) ⇒ onu import eden korpus
  CI'da ImportError ile KIRMIZI yanar. Prior-art zaten vardı: `reviewer_tip_kapsam`
  docstring'i *"Neden import değil: atom.py MCP SDK'sini çeker; CI'da o paket YOK"*
  diyor. ⇒ Yeni korpus yazarken **CI'nın kurduğu bağımlılıkları ÖLÇ**; gerekiyorsa B26
  reçetesiyle AST'den ayıkla (dekoratörü ATLA). `_profile.py` güvenlidir (yalnız
  `utils.project_config`). Canlı ölçüm gereken vektör `mcp` varsa koşar, yoksa
  **`[OLCULEMEDI]`** satırı basar — sessiz SKIP değil, üçüncü değer; kapsamı AST vektörü taşır.
  **Simülasyon reçetesi:** `PYTHONPATH=<tmp>` altına `mcp/__init__.py` → `raise ImportError`
  koy, korpusu koş; A/B vektörleri hâlâ ölçmeli.

- ⛔ **`KURULAMADI` ≠ `KACTI` (çökme ≠ FAIL — kendi korpusumda yaşandı):** mutasyon
  KURULAMAZSA (ör. kardeş mutant dosya yazıldıktan sonra kayboldu → `FileNotFoundError`)
  eski kalıp `yakalandi=False` atayıp bunu *"mutasyon KAÇTI"* diye raporluyordu — yani
  **aracın bozulmasını korpusun zayıflığı** sanıyordu. Üçüncü değer şart: ayrı
  `kurulamadi` listesi + ayrı FAIL satırı. Ayrıca kardeş mutant **yazımdan sonra
  OKUNARAK doğrulanır** (yazımın hatasız dönmesi dosyanın orada olduğunu kanıtlamaz).

- ⛔ **TIER VEKTÖRLERİ İMPORT-ANINDA KİRLENİR (K4 sınıfının İKİNCİ üyesi, ölçüldü):**
  `conn_cift_anahtar` `sal.get_conn_path`i yönlendiriyordu ama **geç kalıyordu**:
  `import sap_adt_lib` İMPORT ANINDA `find_conn_file()` + `load_dotenv()` koşar; repo
  kökünde bir `.conn_adt` varsa `ADT_SAP_TIER=DEV` `os.environ`a yazılır ve yönlendirme
  kurulmadan tier ZATEN kirlenir ⇒ *"tier YOK → UNKNOWN"* vektörü **DEV** okur.
  Süit koşum ORTASINDA (ölçüldü: ~39. saniye, 1087 B) repo köküne yazdığı için bu
  **aralıklı** bir kırmızıydı: fixture önce koşarsa geçer, sonra koşarsa düşer.
  Fix: import ÖNCESİ `CLAUDE_PROJECT_DIR`i kuma çevir. Kanıt (kirli kök varken):
  fix öncesi **5/6** (`tier=DEV`), fix sonrası **6/6**; süit **3 ardışık koşum 144/144**.
  ⚠ Ders: *"monkeypatch ile yönlendirdim"* yetmez — **import anındaki yan etki** daha
  erken koşar. Yönlendirmenin İMPORT'TAN ÖNCE mi sonra mı kurulduğunu ölç.

- ⚠ **DOĞRULANAMADI:** K6 canlı `/activation` kabulü (B11) · K7 gerçek UI5/playwright
  doğruluğu (B15) · K8① canlı Bash düzenlemesinde ateşleme (matcher META-İNFRA,
  kurulmadı — `settings.template.json` kararı lider/kullanıcıda).

## B30 — PARTİ-4b: advisory gate sözleşmesi (K5) + DOC-FS-06 → 06a/06b bölünmesi (K8③)
```bash
python tests/fixtures/byassoc_advisory/run.py           # 10 senaryo + 6 mutasyon, exit 0
python scripts/validators/check_rap_byassoc_keys_only.py --selftest   # gömülü kırmızı/yeşil
python scripts/validators/check_rule_gate_coverage.py   # 62 iddia (59 bloklayıcı · 3 advisory)
python tests/run_fixture_tests.py                       # 145/145
```
- ⛔⛔ **SİLİNEMEZ VEKTÖRLER (POZİTİF KONTROL BORCU).** K5'te değişen şey bir *gevşetme
  değil* **dürüstlük düzeltmesidir** (default `exit 0` AYNEN korundu), ama yeni bir opt-in
  yol açıldı ⇒ "kapıyı körletmedim" iddiası kanıt ister:
  | Vektör | Ne kanıtlar |
  |---|---|
  | **S1** bulgu VARKEN default exit 0 | canlı 2 **meşru** kod hâlâ bloklanmıyor (davranış değişmezliği) |
  | **S2** aynı korpus `--bulguda-exit1` → exit 1 | gate artık gerçekten **fixture'lanabilir** (eski engel kalktı) |
  | **S3** `--strict` → exit 0 | **kazara terfi** yolu kapalı |
  | **S4a/S4b** temiz korpus her iki modda 0 | bayrak "her şeyi kırmıyor" |
  | **S8** coverage kendini advisory İLAN ETMEZ | sahte-beyan çapası (aşağıya bak) |
- ⭐ **SINIR MUTASYONU M2** (`--strict` de exit 1 versin) korpusun en önemli vektörüdür:
  bayrağın ADI bir tasarım kararıdır. `run_all_validators --strict` bayrağı **TÜM**
  validator'lara iletir; gate'i oradan hard'a terfi ettirmek terfi kararını kazara bir
  ÇAĞIRANIN eline verirdi (ADR 0019 §54 shakeout dersi). M2 yeşil kalırsa ad yeniden
  `--strict`e kaymış demektir. **M3** (default'u hard yap) davranış-değişmezliği çivisidir.
- ⚠ **`# GATE-SEVERITY:` SATIR-BAŞI ÇAPASI ZORUNLU** (`^[ \t]*#`, MULTILINE). İlk sürüm
  çıplak `#\s*GATE-SEVERITY:` idi ve **düz metin içindeki anışı da beyan sandı**: bu
  markörü TARİF eden `check_rule_gate_coverage`'ın **kendi docstring'i**, HARD olan o
  gate'i "advisory" ilan etti (ölçüldü: özet "2 advisory" derken biri sahteydi).
  Sınıf: *bir markörü tarif eden metin, onu beyan etmiş sayılamaz.* **S8 + M6** çivi.
- ⭐ **SAFE DESENİNİ SINAYAN TEK VEKTÖR** `ok_all_fields_but_from_kelimesi_var`
  (`ALL FIELDS WITH CORRESPONDING #( lt_keys FROM lt_source )`). İlk korpusta YOKTU ve
  **M5 (SAFE'i sök) hiçbir senaryoyu kırmadı** — yani korpus SAFE'i hiç sınamıyordu.
  Sebep: temiz vektörlerin hiçbirinde `FROM` **kelimesi** geçmiyordu, dolayısıyla
  `USES_FROM` tek başına eliyordu. Gerçek işi gören ayrım ancak ikisi bir aradayken görülür.
- ⚠ **MUTANT KARDEŞ ADI FIXTURE ADIYLA ÖNEKLENİR** (`_mutant_byassoc_advisory.py` /
  `_mutant_byassoc_coverage.py`). Gerekçe ölçüldü: repoda `_mutant_post_validate.py` adını
  **İKİ ayrı fixture** (`fs_docstd` + `hook_bash_ve_stderr_kapsami`) paylaşıyor — o
  çarpışma sınıfına katılmamak için ad benzersiz tutuldu (bkz. kuyruk kaydı).
- **DOC-FS-06 → 06a/06b:** `06a` = §1.1 satır uzunluğu (**ölçülebilir**, gate'li, ≤400
  karakter) · `06b` = 11-B birikmemesi + yayılım tablosunun tamlığı (**reviewer yargısı**,
  script YOK ve olamaz). Gate `# ENFORCES: DOC-FS-05, DOC-FS-06a` beyan eder; `06b`
  checklist'te gate kolonu OLMADAN durur ⇒ coverage onu auto-gate saymaz (iddia 61→**62**,
  şişme değil **doğru yönde artış**: 06a gerçekten gate'li).
- **Dokunulursa BİRLİKTE koşulacaklar:** `check_rap_byassoc_keys_only.py` →
  `byassoc_advisory` **VE** `validator_kapsam_paydasi` (biri exit sözleşmesini, öteki
  payda sözleşmesini ölçer; HARİTA ikisini de bağlar). `check_rule_gate_coverage.py` →
  `byassoc_advisory`. `check_fs_no_analysis_log.py` → `fs_docstd` **VE**
  `gevsetme_pozitif_kontrol` (B9b/B28 zaten bağlıyor).

## B31 — `hook_gate_coverage` korpusu (ADR 0019 coverage'ın ÜÇ katmanı: hook · matcher · id)

> ⚠ **Bu reçete 2026-08-22'de GEÇ yazıldı.** Korpus iki tur boyunca büyüdü ama `infra-test-recipes`'e
> hiç girmedi; bir infra-expert **F0 adımında arayıp bulamadı** ve bunu bulgu olarak raporladı.
> ⛔ **Ders:** fixture yazmak, reçetesini yazmadan **yarım iştir** — F0 okuması reçeteye bakar,
> fixture'ın kendi docstring'ine değil.

**Koşum:** `python tests/fixtures/hook_gate_coverage/run.py` → **18 vektör**, exit 0.
Süitten: `python tests/run_fixture_tests.py` (OZEL_TESTLER üyesi).

### Neyi koruyor — üç ayrı katman, biri diğerini KAPSAMAZ

| Katman | Soru | Anahtar vektör |
|---|---|---|
| **hook** | Hook dosyası var mı · şablona kablolu mu · `# ENFORCES:` beyanlı mı | `S5` MISSING (`hayalet.py`) · `S4` ORPHAN · `S3`/`S16` UNDECLARED |
| **matcher** | Kodda **adı geçen** her tool, şablondaki matcher'la o hook'a **yönleniyor** mu | `S13` temiz · **`S14`** delik · **`S18`** ölü-dışlama |
| **id** | `# ENFORCES:` satırından **hangi token'lar** id sayılıyor | `S11` aşırı-dar · `S12` sınırsız |

⛔ **`S14` niçin ayrı bir dalı gerektiriyor (silinemez gerekçe):** vektör **kablolu** bir hook kurar
(⇒ `ORPHAN=0`) ama matcher'ı kodun işlediği tool'u yönlendirmez. Yani **ORPHAN dalı bu sınıfı
YAKALAYAMAZ**. Tarihsel vaka: bir guard'a PowerShell desteği eklendi, **29 senaryoluk test yeşil
verdi, PR merge edildi**, hook PowerShell'de **hiç tetiklenmedi** (`playbook/lessons-learned.md`
PATTERN #12 — *"kod-seviyesi koruma ≠ korunuyor"*).

### ⚖ ŞİDDET AYRIMI — `ÖLÇÜLEMEDİ`nin üç kaynağı AYNI SINIF DEĞİL

| Kaynak | Kusur nerede | `rc` |
|---|---|---|
| Bozuk `settings.template.json` (`S7`) | ölçüm imkânsız, gate işlevsiz | **1** |
| Ayrıştırılamayan hook dosyası (`S15`) | **hook'un kendisi bozuk** | **1** |
| Gate hook'un tool kümesini **okuyamıyor** (`S17`) | **hook DOĞRU, gate sınırlı** | **0** ⚠ |

⛔ **Üçüncüsü BİLEREK bloklamaz (karar 2026-08-22).** `frozenset({...})` · ters karşılaştırma ·
fonksiyon-içi sabit · sabit-birleştirme gate tarafından **çözülemez** ve bu **kalıcı bir sınırdır**
(tanıma yeteneği bilerek genişletilmedi — *tamlık değil dürüstlük*). Bloklasaydı tek "onarım"
*"geçerli Python'unu gate okuyabilsin diye tuple'a çevir"* olurdu — aracın kuyruğunun köpeği
sallaması. `frozenset` bu evde **yerleşik deyim** (`infra_write_guard` · `pre_tool_guard`).
⇒ Kör hook **`[ÖLÇÜLEMEDİ]` satırında adıyla görünür**, ama commit'i durdurmaz.
⛔ Bu **gevşetme DEĞİLDİR**: kör hook düne kadar **hiç görünmüyordu** ve *"tool ayrımı yapmıyor"*
kovasına düşüp **yanlış biçimde temiz** sayılıyordu (`--mutasyon-kor-kovada` tam bunu çiviler).

### Mutasyonlar — **14 kip**, hiçbiri diğerini kapsamıyor

> ⚠ Sayı ve harita **araçtan** alınmıştır (`--mutasyon-ZIRVA` geçerli kip listesini basar), elle yazılmamıştır.

| Kip | Düşürdüğü vektör(ler) | Neyi çiviliyor |
|---|---|---|
| `--mutasyon-optout-genis` | `S16` | Muafiyet **yalnız** kablolamayı kapsar, `UNDECLARED`'ı **değil** |
| `--mutasyon-optout-yok` | `S10` `S16` | Muaf giriş PASS etmeli (gate merdiveni **adım-6**) |
| `--mutasyon-kor-sessiz` | `S17` | Kör-yazım **görünmeli** |
| `--mutasyon-kor-kovada` | `S17` | Kör-yazım **doğru kovaya** düşmeli (ayrı değişmez — `exit=0` ile düşer) |
| **`--mutasyon-kor-bloklar`** | `S17` | ⭐ **Kör-yazım BLOKLAYICIYA terfi etmesin** (`exit=1` ile düşer). **Turun merkezî şiddet kararının tek çivisi** — bu satır silinirse karar sessizce geri alınabilir |
| `--mutasyon-mesaj-tek-secenek` | `S18` | Bulgu **İKİ** onarım seçeneği vermeli |
| `--mutasyon-id-sinirsiz` | `S12` | Yeterince daralttık mı |
| `--mutasyon-id-asiri-dar` | `S11` | **Fazla mı** daralttık (ters yön — ayrı değişmez) |
| `--mutasyon-capa-yok` | `S6` | `ENFORCES` satır-başı çapası |
| `--mutasyon-hook-katmani-yok` | `S3` `S4` `S5` `S6` `S16` | Hook katmanının tamamı |
| `--mutasyon-hook-parse-sessiz` | `S15` | Ayrıştırılamayan hook **bloklamalı** |
| `--mutasyon-olcum-sessiz` | `S7` | Bozuk şablon **bloklamalı** (ölçüm hatası sessiz geçmesin) |
| `--mutasyon-matcher-katmani-yok` | `S14` `S15` `S18` | Matcher katmanının tamamı |
| `--mutasyon-matcher-adi-uydur` | `S13` `S14` `S18` | Tool adı **uydurulmasın** |

⚠ **Bu harita ÖLÇÜLDÜ** (14 mutasyon tek tek koşuldu, `DOĞRULANAMADI=0`), elle yazılmadı.
İlk yazımında **elle** yazılmıştı ve **beş noktada yanlıştı** — kapı ölçüp düzeltti.
⛔ **Ders:** reçete, koruduğu korpusun *"tek kaynağı"* olduğunu iddia ediyorsa (F0 okuması buraya
bakar), yanlışlığı **azami kaldıraçtadır**. Reçete satırı yazarken aracın kendi çıktısını kopyala.

⛔ **Bilinmeyen `--mutasyon-*` kipi REDDEDİLİR** (`raise SystemExit(<str>)` ⇒ **`rc=1`**) — sessiz tam-puan yok.
⚠ Kip adları **tam** yazılır (`--mutasyon-olcum-sessiz`); kısaltılmış hâli (`--olcum-sessiz`) reddedilir.

### ⚠ Bu korpusa dokunmadan önce

1. **`OPT_OUT` canlıda BOŞ.** `S4`↔`S10` ve **`S3`↔`S16`** **ikizdir**: biri muafiyetsiz, öteki muafiyetli
   aynı ağacı kurar. Birini silmek ötekini **anlamsız** kılar.
2. **`REPO = Path(__file__).resolve().parents[2]` MEŞRUDUR** (CORE-03: core'un kendi varlıkları).
   ⛔ `project_config.project_root()`'a **çevirme** — gate **sessizce boş tarar**.
3. Beklenen tool kümesi **AST'den türetilir, elle tablo YOKTUR.** Elle tablo denenmişti ve
   **yanlıştı** (5 sabitten 3'ünün adı yok, 2 hook atlanmış) ⇒ gate iki sabiti bulamayıp
   sessizce boş tarardı. **Envanteri yapıdan türet, metin deseninden değil.**

## B32 — `worktype_alt_tur` korpusu (worktype hatırlatıcısı ALT-TÜRE bakar)

**Ne koruyor:** `sap_worktype_hint`, SAP-yazma anında obje-tipinden checklist hatırlatır.
Obje tipi **iş türünü bitirmez**: aynı `ddls` altında `abstract entity` ile `view entity`
FARKLI reçetelerdir ve `adt-cds.md` §ABSTRACT ENTITY, kanonik bölümün önerdiği araçların
abstract'ta **çalışmadığını** yazar. Eksen artefaktın **kendi bildirimini** okur (brifing
metnini DEĞİL — o sınıf bu evde iki kez çürütüldü).

**Ölçülmüş taban (2026-08-22, gerçek artefakt korpusu — sentetik değil):** 292 canlı
`.cds/.bdef/.srvd` → **precision %100 · recall %100** (42 abstract entity; 250 diğer
artefaktta 0 yanlış işaretçi). Ölçüm sırasında **iki gerçek FP** bulundu ve kapatıldı:
(a) tüm satır taranınca düz view-entity `select from` → §T3 tuzak notu; (b) başlıktaki
KOD PARÇASI yüzünden `define root view entity` → §ABSTRACT ENTITY (292'nin **30'u**).
Ayrıca 60-satır penceresi 2 abstract entity'yi kaçırıyordu (bildirim 92./117. satır).

⛔ **SİLİNMEZ ÇAPALAR:** `N1b` (view-entity §T3'e yollanmaz) · `N2` (`define root view
entity` ABSTRACT'a yollanmaz) — ikisi de GERÇEK korpusta ölçülmüş FP'lerdir, sentetik
değildir. `T1` (hatırlatıcının andığı her reçete yolu açılabilir = tazelik) ve `S1`
(yeni bölüm ELLE sözlüğe eklenmeden çözülür = "ayrı sözlük yok" sözleşmesi) de silinemez.

**Mutasyonlar — 4 kip, hiçbiri diğerini kapsamaz:** `--mutasyon` (alt-tür sök) → 14/18 ·
`--mutasyon-kodspan` → 17/18 (yalnız N2) · `--mutasyon-pencere` → 16/18 (P1/P3) ·
`--mutasyon-dedup` → 17/18 (yalnız D1). ⚠ `_ikili`'nin obje-adı kesmesi bugün **bağımsız
olarak ölçülemiyor** (kod-parçası süzgeci aynı yolu kapatıyor) — savunma-derinliği
örtüşmesi, kaynakta not düşüldü; mutasyon kipi AÇILMADI (kurulamayan mutasyon "kaçtı"
diye raporlanmaz).

**Nasıl koşulur:** `python tests/fixtures/worktype_alt_tur/run.py [--mutasyon…]`.
Gerçek-korpus ölçümünü tekrarlamak için: hook'u import edip `_alt_tur`'ü projelerin
`SOURCE_CODES/**` artefaktlarına uygula; yer-gerçeği = kaynakta `define [root] abstract
entity` regex'i (matcher'dan BAĞIMSIZ).

## B33 — İÇERİK-VALIDATOR NORMALİZE TARAMA KATMANI (`scripts/utils/kaynak_tarama.py` + 6 tüketici)

> 2026-08-28 adversarial bug-avı **B2 ailesi**. Bu bölüm **6 validator'ün ORTAK paydasını**
> anlatır: `check_no_rap_commit` · `check_amdp_comment_apostrophe` ·
> `check_cds_srvd_comment_syntax` · `check_filter_search_pattern` ·
> `check_ui5_freestyle_traps` · `check_method_param_type_c`.

### Neyi koruyor — üç sınıf, biri diğerini KAPSAMAZ
| Sınıf | Belirti | Yön | Nerede ölçülür |
|---|---|---|---|
| **Satır-kapsamı** | çok-satırlı dil ifadesi desene takılmaz | **kaçış** (gate kör) | `rap_commit_ifade_kapsami` P1/P2 · `imza_cok_satirli_type_c` P1/P2 |
| **Yorum-durumu** | `/* */` bloğunun İÇİ kod sayılır | **yanlış-pozitif** (build durur) | `filtre_yorum_ve_tirnak` N1/N2 · `ui5_blok_yorumu` N1/N2/N4 |
| **Literal-durumu** | literal içi anahtar ihlal sanılır / literal içi tırnak satırı yutar | **iki yönlü** | `rap_commit_ifade_kapsami` N1/E1 · `amdp_satir_sonu_yorumu` N4/N6 |

⛔ **DOKUNMADAN ÖNCE:** `kaynak_tarama.py` ALTI gate'in davranışını taşır. Değiştirirsen
`--degisen scripts/utils/kaynak_tarama.py` **altısının korpusunu birden** seçer (HARITA'da
kablolu). Tek fixture'ın yeşili "katman sağlam" DEMEK DEĞİLDİR.

### Koşum
```bash
# 1) ORTAK katmanın tüm tüketicileri (HARITA üzerinden seçilir)
python tests/run_fixture_tests.py --degisen scripts/utils/kaynak_tarama.py

# 2) Tek tek (her biri kendi P/K/E/N vektörlerini içeride koşar)
python tests/fixtures/rap_commit_ifade_kapsami/run.py     # 16/16
python tests/fixtures/amdp_satir_sonu_yorumu/run.py       # 11/11
python tests/fixtures/cds_uzanti_kapsami/run.py           #  9/9
python tests/fixtures/filtre_yorum_ve_tirnak/run.py       # 12/12
python tests/fixtures/ui5_blok_yorumu/run.py              #  9/9
python tests/fixtures/imza_cok_satirli_type_c/run.py      #  9/9

# 3) MUTASYON — taban sürüme karşı (tüm fixture'lar `B2_GATE_KOK` env'ini destekler)
mkdir -p /tmp/eski && cp -r scripts /tmp/eski/scripts
rm -f /tmp/eski/scripts/utils/kaynak_tarama.py
for v in check_no_rap_commit check_amdp_comment_apostrophe check_cds_srvd_comment_syntax \
         check_filter_search_pattern check_ui5_freestyle_traps check_method_param_type_c; do
  git show <taban-sha>:scripts/validators/$v.py > /tmp/eski/scripts/validators/$v.py
done
B2_GATE_KOK=/tmp/eski/scripts/validators python tests/fixtures/<ad>/run.py
```
⚠ Mutasyon **gerçek kaynağa yazılmaz** — izole ağaç kurulur (kalıntı komşuyu kirletmesin).
`kaynak_tarama.py` izole ağaçtan SİLİNİR: eski validator'lar onu import etmiyordu; dursaydı
"taban" iddiası yalan olurdu.

**Beklenen mutasyon sonuçları** (2026-08-28 taban `b2ab7f1`; hiçbiri diğerini kapsamaz):
`rap_commit_ifade_kapsami` **8/16** (düşen: P1·P2·E1·E2·N1·N6 + S1/S2 yapısal) ·
`amdp_satir_sonu_yorumu` **9/11** (P1·E1) · `cds_uzanti_kapsami` **5/9** (P1·P2·P3 + S1) ·
`filtre_yorum_ve_tirnak` **6/12** (P1·P2·E2·N1·N2 + S1) · `ui5_blok_yorumu` **6/9**
(N1·N2·N4) · `imza_cok_satirli_type_c` **5/9** (P1·P2·E1·N3).

### ⛔ SİLİNEMEZ ÇAPALAR (her biri ÖLÇÜLMÜŞ bir sınırı temsil eder)
- `rap_commit_ifade_kapsami` **K2** — `CALL FUNCTION 'BAPI_TRANSACTION_COMMIT'`: FM adı
  ABAP'ta **zaten literal içinde** yazılır. Literal temizliği bu kümeye uygulanırsa gerçek
  pozitif KAYBOLUR. İFADE/KİMLİK ayrımının tek kanıtı budur (+ S1/S2 yapısal çapa).
- `rap_commit_ifade_kapsami` **N5** (`COMMIT.` + `work = 1.`) ve
  `imza_cok_satirli_type_c` **N1** (`TYPE c.` + ayrı ifadede `LENGTH`) — mantıksal
  birleştirmenin SINIRI. Düşerse gate her komşu token'a bağırır.
- `amdp_satir_sonu_yorumu` **N2/N3** — AMDP gövdesi DIŞINDAKİ ABAP yorumlarında apostrof
  MEŞRUDUR. Gövde sınırı olmadan gate her Türkçe ABAP yorumuna bağırırdı.
  **K2** ise eski satır-başı kuralının KALDIRILMADIĞINI çiviler (ekleme, değiştirme değil).
- `filtre_yorum_ve_tirnak` **E1** / `ui5_blok_yorumu` **E1** — blok yorumu KAPANDIKTAN
  sonraki gerçek ihlal. Blok durumu "açık kalırsa" dosyanın gerisi sessizce körelir;
  bu, düzelttiğimiz FP'den DAHA KÖTÜ bir kaçış olurdu.
- `cds_uzanti_kapsami` **S2** — `.dcl`/`.bdef` BİLİNÇLİ olarak kapsam dışıdır. Ölçüldü
  (0 bulgu) ama ayrı artefakt sınıflarıdır; emsal: 2026-08-01 `check_package_naming` turunda
  `.srvd` 15 FP nedeniyle EKLENMEMİŞTİ. Genişletme kanıtla yapılır, refleksle değil.

### ⚠ Bilinen SINIRLAR (bu turda KAPATILMADI — "ölçüldü ama dokunulmadı")
1. `check_ui5_freestyle_traps` **XML dalı** (T2/T3) hâlâ ham satır bazlıdır: `<!-- -->`
   içindeki `type="Number"` / `<core:Title` WARN üretir. WARN build durdurmaz ⇒ öncelik
   düşük, ama sınıf aynıdır.
2. `check_filter_search_pattern` `_CASE_SENS` alt-dizge eşleşir: `notCaseSensitive: false`
   **hem eski hem yeni** desende yakalanır. Düzeltmesi desen DARALTMASI = ayrı gevşetme
   kararı gerektirir.
3. `js_kod` string durumunu **satır sonunda sıfırlar** (template literal dahil). Dengesiz
   tırnak (ör. regex literali içindeki `'`) yalnız O SATIRI etkiler — hasarı sınırlı tutmak
   için bilinçli seçim; tam JS ayrıştırıcısı DEĞİLDİR.
4. ABAP tam-satır yorumu tespiti mevcut davranışla aynı bırakıldı
   (`lstrip().startswith("*")`); ABAP'ın gerçek kuralı "sütun 1'de `*`"tır.

### Canlı korpus tabanı (tüketici projede, 2026-08-28)
`check_no_rap_commit` 0 ERROR / **6 WARN** · `check_ui5_freestyle_traps` 0 ERROR / **7 WARN** ·
diğer dördü **0 bulgu**. Kapsam paydaları: 81 · 321 (eskiden 280) · 124 · 283.
**Fix öncesi/sonrası çıktı BAYT AYNI** (tek istisna: cds/srvd payda satırı 280→321).
