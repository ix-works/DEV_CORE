# 0016 — Source DRIFT Önleme: Repo ↔ Canlı SAP Senkron (Kod-Gate)

**Durum:** Kabul edildi (2026-06-16)
**Bağlam ADR'leri:** [0005](0005-sap-standart-obje-koruma-ve-sistem-state-yasaklari.md) (yasaklar/guardrail), [0006](0006-reviewer-pre-flight.md) (reviewer pre-flight), [0007](0007-sap-adt-mcp-server.md) (MCP server), [0010](0010-tier-bazli-readonly-guard.md) (kod-gate deseni), [0013](0013-kaynak-referans-dokuman-ayrimi-ref_docs.md) (ref_docs ayrımı)
**Pilot/kanıt:** ZSD001_UI_BOOKING.srvd (canlı drift bilinen vaka), ZSD001_CLC

---

## Bağlam

Yerel repo kaynak dosyaları (`.srvd`/`.cds`/`.ddls`/`.abap`/`.bdef` ...) canlı SAP'nin
**aktif sürümünden** sessizce ayrışabiliyor. Somut vaka: `ZSD001_UI_BOOKING.srvd` yerelde
8 expose taşırken canlıda 13 expose aktifti (başka bir oturum/ajan canlıya ekleme yapmış,
repo güncellenmemiş).

**Tehlike:** Bu durumda yerel dosyayı `adt_push_source` ile push etmek, canlıdaki
**belgelenmemiş değişiklikleri SESSİZCE EZER/SİLER** — geri-alınamaz veri/konfigürasyon
kaybı. Reviewer (ADR 0006) bunu yakalamaz; reviewer source'un *kendi* kalitesine bakar,
canlıyla *kıyaslamaz*. Sadece markdown/uyarı yetmez — kanıtlanmış kayıp riski → **kod-gate**
gerekir (bypass yok, ADR 0005/0010 deseni).

İkincil tuzak: ham diff CRLF↔LF farkını her satır sayar → **sahte drift** (template-drift
CRLF şişmesi dersi). Normalizasyon ŞART.

## Karar

> ### ⚠️ REVİZE (2026-06-16) — model değişti: pre-push BLOCK yerine PULL-BEFORE-EDIT
> İlk tasarım (M1 pre-push drift-block + M2 post-write sync + M3 validator) **ilk gerçek
> kullanımda KUSURLU çıktı:** M1, `normalize(canlı) != normalize(repo)` symmetric kıyası
> yaptığı için **KASITLI edit'i de blokluyordu** — bir objeyi düzenleyip push ettiğinde
> repo zaten canlıdan FARKLIDIR (push'un amacı bu). Yani M1, 404/no-op dışındaki HER
> meşru source push'unu blokladı (railway kampanyası ADIM 1'de yakalandı). M1 "bayat-repo
> (clobber)" ile "kasıtlı-edit"i ayıramaz; doğru referans working-tree değil **baseline**
> olmalıydı (bkz. "Reddedilen" altı). **Karar: M1 + M2 + M3 KALDIRILDI; koruma push-anından
> EDIT-ÖNCESİNE taşındı.** Aşağıdaki yeni model geçerlidir.

**Yeni model — PULL-BEFORE-EDIT (edit-öncesi tazelik):**

### P1 — PreToolUse(Edit|Write) gate (`scripts/hooks/pull_before_edit.py`)
Yönetilen bir SAP source dosyasını (ERP/ altı, source uzantısı) düzenlemeden ÖNCE, o
objenin canlı GÜNCEL hali bu SEANSTA çekilmiş/yazılmış olmalı. Değilse edit **BLOKLANIR**
(exit 2) ve agent önce `sap_sync_pull.py` ile çeker → working-copy daima TAZE canlıdan
türer → push, canlıdaki belgelenmemiş bir değişikliği ezmez. Subagent edit'lerinde de
tetiklenir (kanıtlandı 2026-06-16: project-level PreToolUse subagent tool-çağrısında fire eder).
**Muafiyet (sessiz GEÇ):** SAP-dışı dosya · ref_docs/docs/.tmp · class alt-include · dosya
YOK (yeni obje) · **git-DIRTY (commit'siz WIP = zaten üstünde çalışıyorsun → pull EZMESİN)** ·
session_id/store yoksa fail-safe.

### P2 — Sync helper (`scripts/sap_sync_pull.py`)
Canlı AKTİF source'u çek → repo dosyasına yaz (CRLF korur, **tip-farkında** dosya eşleme:
aynı-adlı `.cds`/`.bdef` çakışmasını object_type ile çözer) → seans-tazelik store'una
(`.claude/.session_fresh.json`) damgala. Source-based tipler `sync_repo_from_live`; XML-DDIC
(struct/table/dtel/domain) `get_ddic_object`. **`--offline`** escape: SAP erişilemezken
fetch'siz taze damgalar (canlıdan ezme riskini bilerek kabul). Seans-bazlı: store başka
seanstansa sıfırlanır.

### Korunan readback-doğrulama
"Push sonrası SAP gerçekten ne sakladı?" doğrulaması (inline-empty / sessiz-format dönüşümü
tuzakları) **runbook/gateway disiplini** olarak korunur (`adt_get` readback) — bu repo-sync
DEĞİL, doğrulamadır; M2'nin repo-writeback'i ile karıştırılmamalı.

### Normalizasyon (ŞART)
CRLF↔LF + satır-sonu trailing whitespace + baş/son boş satır farkı YOK SAYILIR (sahte
drift'i önler). İç içerik (eklenen/silinen expose/alan/satır) KORUNUR — gerçek drift yine
yakalanır. Intra-line whitespace ve case KASITLI normalize EDİLMEZ: gerçek drift'i (ör.
yeniden sıralanmış expose) maskelememek için güvenli taraf seçildi — biçim-farkı soft
uyarı olarak görünür, push'u sadece o objeyi push ederken bloklar.

### Kapsam dışı (sahte-pozitif önleme)
- `ref_docs/`/`docs/`/`.tmp/` altındakiler (ADR 0013: deploy edilebilir kaynak değil) → muaf.
- Class ALT-source include'ları (`.ccimp`/`.ccdef`/`.ccau`/`.clas.locals_*`/`.clas.testclasses`)
  ayrı ADT URL'lerine map olur (`/includes/...`, `/source/main` DEĞİL) → basename eşlemesinde elenir.

## Enforcement (yeni model — pull-before-edit)

- **P1** PreToolUse(Edit|Write) hook (`scripts/hooks/pull_before_edit.py`) settings.json'da wire'lı;
  SAP source düzenlemeden önce bayatsa exit 2 (blok). **Subagent edit'lerinde de fire eder**
  (kanıtlandı 2026-06-16: project-level PreToolUse subagent Bash'inde bloklandı). Edit, önceden
  Read'i + pull dosyayı değiştirince re-Read'i zorunlu kıldığından **FİNAL edit daima taze
  içeriğe** uygulanır (bayat-push deliği yok).
- **P2** `scripts/sap_sync_pull.py` — canlı çek + repo'ya yaz (CRLF-korur, tip-farkında) + seans
  damgala (`.claude/.session_fresh.json`); `--session` SessionStart marker'ından otomatik.
- **Analiz tazeliği (C)** = editleyen ajan protokolü: görev başında hedef objeyi ANALİZDEN ÖNCE
  pull et. Hook = backstop. (`.claude/agents/{backend-expert,adt-gateway,sap-feature}.md` güncellendi.)
- **KALDIRILDI:** M1 (pre-push drift-block), M2 (post-write repo-sync), M3 (drift validator) — sebep banner'da.

## Sonuçlar

- `+` Kasıtlı edit artık bloklanmaz; normal edit→push akışı çalışır (M1'in kör-noktası giderildi).
- `+` Analiz+değişiklik TAZE koda dayanır (görev-başı pull); push, canlıdaki belgelenmemiş değişikliği ezme riskini düşürür.
- `−` Best-effort (hard-gate değil): eşzamanlı canlı-edit penceresi kalır (kabul — gerçek hayatta da olur). Hook = emniyet ağı.

## Test (kanıt)

`pull_before_edit.py` (2026-06-16, canlı): non-SAP→GEÇ · temiz+bayat managed source→BLOK(exit2)+mesaj ·
git-dirty WIP→GEÇ · taze→GEÇ · farklı-seans→BLOK (session-match fail-safe). `sap_sync_pull.py`:
--offline damgalar (UTF-8 ok) · marker'dan --session çözer → hook eşleşir → taze. Subagent PreToolUse
fire kanıtı: `pre_tool_guard` subagent Bash'ini bloklamıştı.

## Artefaktlar

- `scripts/hooks/pull_before_edit.py` — PreToolUse(Edit/Write) gate (bayat SAP source → blok + yönlendirme).
- `scripts/sap_sync_pull.py` — pull + repo-yaz + seans-taze damga (`--offline` escape; `--session` marker'dan).
- `scripts/hooks/session_start.py` — seans marker (`.claude/.current_session`) yazar (pull-before-edit için).
- `mcp_servers/sap_adt/tools/atom.py` — M1/M2 wire'ları SÖKÜLDÜ.
- `scripts/source_drift.py` — `find_repo_source_file` artık `object_type`-farkında (name-collision fix; pull helper reuse). compare/normalize çekirdeği korunur.
- `scripts/validators/check_source_drift.py` — DEPRECATED (run_all'dan çıkarıldı; dosya durur).
- CLAUDE.md §7 + `.claude/settings.json` (PreToolUse Edit/Write) — güncellendi.
