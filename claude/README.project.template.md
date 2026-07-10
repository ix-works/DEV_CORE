# <PROJECT_NAME> — DEV_CORE tabanlı proje iskeleti

Bu repo, [`ix-works/DEV_CORE`](https://github.com/ix-works/DEV_CORE) metodoloji
çekirdeğine bağlı bir SAP/ABAP projesidir.

---

## Temel ilke: EDİNME, BAK

Proje metodolojiyi **kopyalamaz**. `core/` adında bir junction ile DEV_CORE'a **bakar**
(ADR 0020). Diskte metodolojinin **tek** kopyası vardır.

```
DEV_CORE\                     ← metodoloji (tek fiziksel kopya)
<PROJECT_NAME>\
  ├── core\             ══► DEV_CORE                      (junction)
  ├── .claude\agents\   ══► DEV_CORE\claude\agents
  ├── .claude\skills\   ══► DEV_CORE\claude\skills
  ├── .claude\commands\ ══► DEV_CORE\claude\commands
  └── .claude\rules\    ══► DEV_CORE\claude\rules         (L1b, glob-tetiklemeli)
```

Core'a düşen bir düzeltme **tüm projelere anında** yansır. Bu repoda metodolojiden tek
satır yoktur — `.gitignore`, pre-commit ve CI (`guard.yml`) bunu üç katmanda zorlar.

---

## Talimat katmanları — neyin ne zaman yüklendiği

| Katman | Nerede | Nasıl yüklenir |
|---|---|---|
| **Anayasa** (KESİN YASAKLAR) | kök `CLAUDE.md`, fiziksel damga | Her oturum; `/compact` sonrası diskten yeniden enjekte |
| **L1a** her-oturum davranışı | `core/CLAUDE.core.md §1.1` | Her oturum (`@import`) |
| **L1b** dosya-türüne bağlı | `core/claude/rules/*.md` | **Eşleşen dosya okununca** (`globs:`) |
| **L1c** derin referans | `core/AGENTS.md` | ⚠ **Otomatik YÜKLENMEZ** — açıkça okunmalı |
| **L2/L3** standart & playbook | `core/standards/`, `core/playbook/` | On-demand |
| **L4** paket kuralı | `<source_root>/<MOD>/<PKG>/.rules.md` | On-demand |

> **Markdown link hiçbir şey yüklemez.** Claude Code `CLAUDE.md` okur, `AGENTS.md` okumaz.
> `.claude/rules/` frontmatter'ında **`globs:`** kullanılır; dokümante `paths:` biçimi
> sessizce çalışmaz (anthropics/claude-code#17204).

---

## DEV_CORE ↔ proje: hangi bilgi nerede yaşar

| Soru | Cevap | Nereye |
|---|---|---|
| Bir **pattern / ADT dersi** öğrendim | Her projede geçerli | **DEV_CORE** → `playbook/` |
| Bir **kural** koydum, atlanamaz olmalı | Her projede geçerli | **DEV_CORE** → `standards/` + bir **gate** (validator/hook) |
| **Mimari karar** (metodoloji) | Her projede geçerli | **DEV_CORE** → `governance/decisions/` (ADR) |
| **Script** yazdım, tekrar lazım | Her projede geçerli | **DEV_CORE** → `scripts/` + playbook referansı |
| **Bu SAP sistemi**, bu müşteri, bu paket | Yalnız bu proje | **Proje** → `project.yaml`, `.conn_adt`, `CLAUDE.md` |
| **İş kuralı** / sprint kararı | Yalnız bu proje | **Proje** → `governance/` |
| Bu **pakete özel** istisna | Yalnız bu paket | **Proje** → `<source_root>/<MOD>/<PKG>/.rules.md` |
| Core kuralını bu projede **daraltmak** | Yalnız bu proje | **Proje** → `playbook-local/` · `standards-local/` · `scripts/validators-local/` |

Karar ağacı: `core/CLAUDE.core.md` §4 ("SORU 0").

### Genericize kuralı — core'a ne giremez

DEV_CORE **public**tir. `pre_tool_guard` + `core_precommit` şunları core'a yazılmaktan
bloklar: müşteri/firma adı, SAP host adı, **SAP kullanıcı adı**, transport numarası,
kişisel handle, **gerçek Z-obje adı**. Kanonik örnek adları (`Z<MOD>000` / `Z<MOD>001`)
bilinçli istisnadır. Kimlik listesi repo ağacının **dışında** yaşar
(`.git/genericize-blocklist`); CI'da `IX_GENERICIZE_BLOCKLIST` secret'ıyla verilir —
liste yoksa gate **fail-closed** durur.

---

## Bu repoda ne var

| Yol | Ne |
|---|---|
| `CLAUDE.md` | İnce loader. Üstünde **KESİN YASAKLAR** fiziksel damgası (ADR 0005/0021), altında `@core/CLAUDE.core.md` |
| `project.yaml` | Proje kimliği: `sap_profile`, `release`, `master_language`, `source_root`. **Core script'leri buradan okur** |
| `.claude/settings.json` | Hook kayıtları; hepsi `scripts/hook_shim.py` üzerinden core'a gider |
| `scripts/hook_shim.py` | Hook köprüsü (junction kopuksa net onarım mesajı) |
| `scripts/git-hooks/pre-commit` | Statik gate ③: core-sızıntı + CORE-INDEX tazeliği + `run_all_validators --quick` |
| `.mcp.json` | SAP ADT MCP server'ı core'dan yükler; bağlantı `.conn_adt`'den |
| `.gitignore` | Sızıntı kilidi + sırlar + runtime state |
| `.github/workflows/guard.yml` | CI: core-leak · validators · behavior-surface |
| `.github/CODEOWNERS` | Davranış-yüzeyi ve gate'ler için code-owner onayı |
| `<source_root>/<MOD>/<PKG>/` | SAP kaynak kodu. Her pakette `.rules.md` (L4) |
| `governance/` | Proje ADR'leri, `deferred-triggers.md`, paket kaydı |

---

## Yeni proje nasıl açılır

**Bu repoyu klonlayıp içini boşaltma.** Kanonik yol `core/PROJECT_BOOTSTRAP.md` STEP 0–6:

```powershell
# STEP 1 — repo + klasör (yalnız repo_mode=full)
gh repo create <ORG>/XYZ --private
git clone https://github.com/<ORG>/XYZ.git C:\IX\XYZ

# STEP 2 — iskeleti ÜRET (kopyalama!)
python C:\IX\DEV_CORE\scripts\init_project.py C:\IX\XYZ --name XYZ --repo-mode full

# STEP 3 — junction'lar + memory seed + pre-commit kablolaması
python C:\IX\DEV_CORE\scripts\team_setup.py --project C:\IX\XYZ

# STEP 4 — proje değerlerini doldur
#   project.yaml  → sap_profile / release / master_language / (cleancore_policy)
#   .conn_adt     → SAP host/client/user   (şablon: core/claude/conn_adt.template)
#   CLAUDE.md     → proje kimliği bölümü
python core/scripts/behavior_manifest.py generate

# STEP 5 — ilk paket
mkdir <source_root>\SD
python core/scripts/bootstrap_package.py ZSD001_CLC --module SD --title "..." --owner "<OWNER>"

# STEP 6 — ilk commit/push, SONRA kabul gate'i (ix_doctor commit+ruleset arar)
git add -A ; git commit -m "chore(bootstrap): XYZ iskeleti" ; git push -u origin main
python core/scripts/ix_doctor.py
```

`repo_mode=local` (yalnız git init) veya `none` (git'siz) seçilirse STEP 1 atlanır.

⚠ **`bootstrap_package.py` modül klasörünü kendisi yaratmaz** — önce `<source_root>/<MOD>`.
⚠ **`--owner` verilmezse** script `git config user.name`'i dosyalara gömer → public repoda
kimlik sızıntısı. Daima `--owner` ver.

---

## STEP 6 sonrası — kabul gate'i

| # | Kanıt | Nasıl |
|---|---|---|
| 1 | Loader + hook'lar çalışıyor | Oturum aç → **ekran teyidi formatı** geliyor |
| 2 | MCP kendi sistemine bağlı | `ping` + read-only `adt_get` → **projenin** SAP sistemi |
| 3 | Validator'lar PASS | `python core/scripts/validators/run_all_validators.py` |
| 4 | Sızıntı kilidi çalışıyor | `git ls-files core/ .claude/agents .claude/rules` → **boş** |
| 5 | Kurulum sağlığı | `python core/scripts/ix_doctor.py` → FAIL yok |
| 6 | **L1b kuralları gerçekten yükleniyor** | Bir `.abap` okut → `.tmp/instructions-loaded.log`'da `path_glob_match` satırı |

SAP bağlantısı olmayan iskelet/LITE projelerde madde 2 (ve `ix_doctor` K5) gerekçeli SKIP.

---

## Ruleset notu (tek geliştirici)

`main-pr-required` ruleset'i 1 onaylayan review ister, ama **GitHub kendi PR'ını
onaylatmaz**. Tek code-owner varsa `bypass_actors=[{OrganizationAdmin, bypass_mode:
pull_request}]` **ŞARTTIR** — yoksa her merge `--admin` bypass'ı olur ve "onay zorunlu"
kuralı fiilen hiçbir onay kaydetmez.

---

## Günlük çalışma

```powershell
python core/scripts/validators/run_all_validators.py   # tüm gate'ler
python core/scripts/ix_doctor.py                       # kurulum sağlığı
python core/scripts/team_setup.py --repair-junctions   # junction koptuysa
```

`main`'e doğrudan push kapalıdır. Her değişiklik: kısa branch → PR → CI → code-owner onayı.

## Sorun giderme

| Belirti | Çözüm |
|---|---|
| Hook "CORE JUNCTION KOPUK" diyor | `python <DEV_CORE>\scripts\team_setup.py --repair-junctions` |
| Ekran teyidi gelmiyor | `CLAUDE.md`'deki `@core/CLAUDE.core.md` import'u + `core` junction'ı |
| MCP yanlış sisteme bağlı | Proje kökündeki `.conn_adt` (env `ADT_SAP_*` override eder) |
| Validator "CORE-modu" diyor | `project.yaml` proje kökünde mi + `sap_profile` dolu mu |
| MCP tool'ları görünmüyor | `project.yaml` → `sap_profile` boş/geçersiz → **fail-closed**, yalnız `ping` açılır (D34d) |
| `.claude/rules/` kuralı uygulanmıyor | `globs:` mi yazdın (`paths:` sessizce çalışmaz)? `.tmp/instructions-loaded.log`'a bak |

---

**Kanonik el kitabı:** `core/PROJECT_BOOTSTRAP.md` · **Mimari:** ADR 0020 (çoklu-proje / junction'lı çekirdek)
