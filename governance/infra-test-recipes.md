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
- `--quick` ≈2,5sn; `IX_VALIDATOR_WORKERS=1` seri = paralel **bayt-eş**; 3-koşum bayt-eş.
- **Bozuk-girdiyle test ZORUNLU:** run_fixture_tests 10/10; yeni validator = fixture-çifti de.
- Sınıf-tuzakları: `Path(__file__)`-kök türetme YASAK (project_config kullan; AST-gate yakalar) · `rglob` YASAK → prune'lu walk (SINIF İKİ KEZ yaşandı) · non-ASCII print → `utf8_konsol()` (C-ENC-01) · yeni hook → template-sync (C-TPL-01).
- Yeni gate açılışı: PATTERN#14 (ilk-koşu ölç → taban-sıfırla → HARD).

## B10 — run_review
- **Tip-haritası tamlığı (en kritik):** her anahtar+eş-anlamlı için `task_for_push()` non-None (None = sessiz-atlama sınıfı).
- Kirli-.bdef → BLOCKER/is_blocker · temiz → PASS · kapsam-dışı prog → task=None (bilinçli).
- SKIP-görünürlüğü: koşmadıysa "PRE-FLIGHT KOŞMADI (sebep)" satırı OLMALI.

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
- struct-create sonrası koşulsuz içerik-verify ("activated" shell'i maskeleyemez).
- Canlı-yazma testleri: yalnız gateway + throwaway-Z; eşzamanlı-gateway varken KOŞMA.
- **Tier (ADR 0010) FAIL-CLOSED:** `python tests/fixtures/tier_fail_closed/run.py` → 24/24, exit 0.
  Değişmezler: tier-satırsız `.conn_adt` → `UNKNOWN` (**DEV DEĞİL**) → mutasyon RED ·
  `ADT_SAP_TIER_OLD=DEV` tuzağı (gerçek satırdan ÖNCE **ve** SONRA) tier'ı GASP EDEMEZ ·
  `require_writable_tier(None|"")` REDDEDER (ikinci fail-open katmanı geri gelmesin) ·
  UNKNOWN'da hassas-OLMAYAN okuma SERBEST kalır (salt-okuma kısıtlanmaz) · statusline
  tier-yoksa `TIER-YOK RO` gösterir. Yeni tier kaynağı eklersen fixture'a satır ekle.

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
