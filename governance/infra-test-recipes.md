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
python tests/run_fixture_tests.py                   # G1 10/10  [✓]
python scripts/inspector.py --self-test             # canary    [✓]
```

## B1 — hook_shim (proje-tarafında yaşar!)
- Konum-uyarısı: shim DEV_CORE'da YOK — `<proje>/scripts/hook_shim.py`; test proje-kökünden.
- Mojibake-regresyonu: `printf '%s' '{"prompt":"GÖREV: şu ekrana kolon ekleyelim"}' | python scripts/hook_shim.py intake_triage` → çıktıda `GÖREV` doğru (GA–REV = stdin-reconfigure geriledi).
- Fail-closed değişmezi: junction-kopukken bloklayıcı hook → **exit 2** (1 değil).
- **`printf` kullan, `echo` KULLANMA** — echo backslash bozar → JSON-fail → fail-safe-0 → "geçti" sanılır (5d6b90d'nin yaşadığı tuzak).

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

## B4 — pull_before_edit
- Bayat-seans SAP-source Edit-payload → **exit 2** ve mesajdaki komut **`core/scripts/sap_sync_pull.py`** (proje-göreli).
- Taze-seans → 0; SAP-dışı → 0; damga **proje-kökü** `.claude` altında (DEV_CORE'a yazıyorsa d2d326d regresyonu).
- `IX_SOURCE_ROOT` farklı-adla hâlâ yakalıyor (4 fixture).

## B5 — skill_injector / worktype_hint / ITG-katmanları
- ITG A/B/C: regex-tetik→marker, backstop-sessiz · keyword-dışı-talep→ilk SAP-tool'da backstop-enjekte · ping/Bash→sessiz.
- Diyakritik: "gelistir" TETİKLER; "istersen"/"isteğe bağlı" TETİKLEMEZ.
- task-notification payload'ı → sessiz. worktype: tip-başına 1 enjeksiyon (struct/tablo AYNI grup!).
- Sınıf-kuralı: keşif ekleyeceksen NATIVE-description'a, hook-regex'ine DEĞİL.

## B6 — post_validate
- HIZLI_KUME 5 sınıf → hızlı-tur; **tablo-DIŞI → TAM tur** (hızlıya düşerse fail-open'a kaydı).
- Türkçe alt-validator çıktısı relay'de bozulmamalı (capture encoding).

## B7 — recall_inject + build_recall_index
- P: "classrun derdi" → PATTERN#19 · RAP-sorgusu → 3-ders · "validator/hook" → infra-howto ilk-sıra.
- N: kısa-prompt sessiz · bozuk-indeks exit-0 (fail-open) · alakasız sessiz.
- Fixture bilinçli YOK (deterministik-LLM'siz) → reçete = sentetik-payload (howto-sistem-denetimi §3).

## B8 — watchdog / pre_compact / post_tool_failure / instructions_log / radar_check
- watchdog: probes-yok → yalnız reach (SAHTE-ALERT üretme); kopuklukta **1** alert (edge); daemon URL-yoksa graceful-exit; launcher proje-kökünü ARG'la geçirir.
- pre_compact çıktısı `systemMessage` (additionalContext ŞEMA-GEÇERSİZ — canlı-kanıtlı).
- post_tool_failure: fail-payload'da merdiven(+5b infra-satırı) · başarıda sessiz.
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

## B19 — .conn_adt YAZICI tarafı (encoding)
- `python tests/fixtures/conn_yazici_encoding/run.py` → 7/7 (locale-bağımsız).
- Değişmez: `.conn_adt` yazan her yol AÇIK `encoding="utf-8"` taşır (AST çapası tüm
  `write_text` çağrılarını denetler). Okuyucular utf-8/utf-8-sig; yazıcı locale'e bırakılırsa
  cp1252'de em-dash → `0x97` → **her `import sap_adt_lib` çöker** (1085 baytlık dosya vakası).
- ⚠ Şablondaki non-ASCII karakter KANARYADIR; ASCII'ye indirgersen test sessizce boşalır (V6).
- FP çapası: dosya BOM ile BAŞLAMAZ (BOM eklemek AV-02 sınıfını geri getirir).

## B20 — lock yanıtı `MODIFICATION_SUPPORT` (sap_adt_lib `_verify_and_return_lock`)
- `python tests/fixtures/lock_modification_support/run.py` → **25/25** · MUTASYON:
  `--mutasyon --ref origin/main` → **16/25** (9 ayırt edici FAIL).
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
- **§12.7 teşhisi 423'te basılır** (`set_object_source`, V16/V16b): E071 sorgusu + **iki kök**
  (transport kaydı **ve** bayat lock handle). 500'de basılmaz (V17 FP çapası). Tek kök dayatmak
  2026-08-09'da bir saat kaybettiren "transport kovalama" sapmasının kendisiydi.
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
- UI5: `.click()` tetiklemez → firePress+model-API; basic-auth header'la; app-içi npm-install YASAK.

## B16 — templates + agents
- Brifing-lint 3-varyant (temiz/şablonsuz/kısa-muaf); Türkçe-FP çıkarsa ÖNCE B1-mojibake.
- **Model beyanı ≠ fiilî:** aynı-oturum spawn oturum-modelini kullanır (tanımlar oturum-başı) → fiilî-doğrulama YENİ oturumda, transcript'ten.
- check_settings_template_sync + check_rule_gate_coverage yeşil (çakışan checklist-no böyle yakalandı: FE-38→39).
