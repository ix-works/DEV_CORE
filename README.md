# DEV_CORE — Canlı Metodoloji Çekirdeği

> **Tek cümlede:** Tüm projelerin ORTAK ve CANLI kullandığı
> SAP-AI geliştirme metodolojisi: standartlar, playbook, script/validator/hook takımı,
> MCP server, agent tanımları ve skill'ler — **tek kaynak-gerçek, kopya YOK**.

## Mimari (ADR 0020 — canlı çekirdek + junction)

```
GitHub                                   Lokal disk (her geliştirici)
ix-works/DEV_CORE  ──clone──►  C:\IX\DEV_CORE\        ← BU repo (working tree = canlı çekirdek)
ix-works/<PROJECT_NAME> ─clone─► C:\IX\<PROJECT_NAME>\
                                 ├─ core ══junction══► C:\IX\DEV_CORE
                                 ├─ CLAUDE.md (ince: @core/CLAUDE.core.md + proje bölümü)
                                 └─ .claude\{agents,skills,commands} ══junction══► DEV_CORE\claude\...
```

- **Canlılık:** Core'daki bir düzeltme, aynı makinedeki TÜM projelere ANINDA yansır
  (junction = tek fiziksel kopya). Manuel port/kopya süreci YOKTUR.
- **Senkron:** Makine başına tek `git pull` (bu clone'da). `session_start` hook'u
  "origin'in gerisindesin" uyarısı verir.
- Projeler bu repoya junction'la BAKAR; proje repolarına core içeriği ASLA commit'lenmez
  (`.gitignore` + `check_core_not_committed` + CI kilidi).

## Depo haritası

| Klasör | İçerik |
|---|---|
| `CLAUDE.core.md` | Çekirdek loader — yasaklar (ADR 0005), session protokolü, SORU 0, gate tablosu. Projelerin ince `CLAUDE.md`'si bunu `@core/...` ile import eder |
| `AGENTS.md` | L1 — agent davranış kuralları (git, ADT işlem sırası, ADT-infra) |
| `standards/` | L2 — kurumsal standartlar (naming, backend, RAP, UI5, klasik dialog, FS/TS, forms…) |
| `playbook/` | L3 — ADT pattern bankası, lessons-learned, checklists, kod template'leri |
| `profiles/` | SAP profil yetenek matrisi (`ecc / s4_private / s4_public / btp_abap`) — içerik `applies_to:` etiketiyle profile bağlanır |
| `scripts/` | Araç takımı: ADT CRUD, validators (`run_all_validators.py`), hooks, gate'ler, deploy, doküman üreticileri |
| `mcp_servers/sap_adt/` | Typed ADT MCP server — server-side ADR 0005 guardrail'li |
| `claude/` | Projelere junction'lanan varlıklar: `agents/`, `skills/`, `commands/`, `memory-seed/` + `settings.template.json`, `CLAUDE.project.template.md`, `hook_shim.template.py` |
| `governance/` | Metodoloji ADR'leri (`decisions/`), agent-teams işletim modeli, tooling envanteri |
| `templates/` | Yeni-paket iskeleti vb. üretim şablonları |

## Kurulum (yeni geliştirici / yeni makine)

**Ön-koşullar (makine-düzeyi — repo bunları GETİRMEZ):** Python ≥3.10 · git ·
Node.js+npm · Claude Code CLI (`claude`). Bunlar kuruluysa gerisi tek komut:

```powershell
git clone https://github.com/ix-works/DEV_CORE.git C:\IX\DEV_CORE
# proje clone'undan sonra, proje kökünde:
python C:\IX\DEV_CORE\scripts\team_setup.py
```

`team_setup` şunları kurar/doğrular: junction'lar + hooksPath + pip-bağımlılıkları +
**Claude Code plugin'leri** (`setup_plugins.py`: ui5 · playwright-MCP · pyright-lsp ·
plugin-dev — makine-düzeyi, clone ile GELMEZ) + **npm CLI'ler** (`playwright-cli`
[tarayıcı-doğrulama + ui-smoke gate'inin temeli, ADR 0017] · ast-grep · mmdc · marp) +
memory-seed + smoke testler. Plugin/CLI adımları NON-FATAL'dır ama FE/UI işine
başlamadan tamamlanmış olmalı (`ix_doctor` bağımlılık katmanı kontrol eder).
Envanter ve "hangi iş → hangi araç": [`governance/tooling-plugins.md`](governance/tooling-plugins.md).

**Playwright iki katmandır (bilinçli):** tercih edilen `playwright-cli` (npm-global binary +
core'daki `claude/skills/playwright-cli` skill'i — token-verimli, ~4x) ; yedek `playwright`
Claude-plugin'i (MCP — ad-hoc debug). UI-doğrulama akışı: [`governance/tooling-plugins.md`](governance/tooling-plugins.md).

Yeni PROJE açılışı: [`PROJECT_BOOTSTRAP.md`](PROJECT_BOOTSTRAP.md) (STEP 0–6 + kabul gate'i).
Kurulum doğrulama: `python scripts/ix_doctor.py` (7-katman sağlık taraması).

## Çalışma kuralları (özet — detay: [`MAINTENANCE.md`](MAINTENANCE.md))

- **Yazma = herkes PR + CI required-check** (lider dahil; `main` branch-protected). Bypass yok.
- **Genericize-on-write:** Bu repoya proje/müşteri kimliği GİREMEZ (sistem adı, kullanıcı,
  paket numaraları → placeholder; `ZSD000`/`ZSD001` çalışan-demo istisnası). Pre-commit
  hook (`scripts/git-hooks/`) + CI tarar.
- **`applies_to` zorunlu:** standards/playbook/checklist dosyaları hangi SAP profillerinde
  geçerli olduğunu frontmatter'da beyan eder.
- **`stable` tag** = bilinen-iyi commit (yalnız lider ilerletir; tag-ruleset korumalı).
  Kırık durumda: `git checkout stable` → dönüş `git switch main`.
- Trunk-based: `main` tek uzun-ömürlü branch; kısa branch'ler aynı gün merge.

## İlişkili repolar

- **[ix-works/template_project](https://github.com/ix-works/template_project)** — *(public)*
  **canlı referans iskelet.** Bu çekirdeğe bağlı bir projenin nasıl göründüğünü gösterir:
  ince `CLAUDE.md`, `project.yaml`, 4 junction, sızıntı kilidi, CI, CODEOWNERS, örnek paket.
  [`PROJECT_BOOTSTRAP.md`](PROJECT_BOOTSTRAP.md) STEP 0–6'nın canlı provasıdır; SAP bağlantısı
  **yoktur**. Yeni proje açarken oraya *bakılır*, oradan **kopyalanmaz** — `init_project.py`
  ile üretilir.

- **Proje repoları** *(private)* — yalnız proje içeriği; metodolojiyi bu repodan
  junction'la kullanırlar. Bir projenin nasıl kurulduğu için yukarıdaki
  `template_project`'e bak.
- Eski dünya repoları — **dondurulmuş tarihsel yedek** (2026-07-08 öncesi; salt-okunur,
  push almaz). Yolları makine-lokaldir (`project.yaml` → `frozen_readonly_paths`).

### Çekirdek ↔ proje: sorumluluk sınırı

| Bu bilgi… | …buraya (DEV_CORE) | …projeye |
|---|---|---|
| Pattern / ADT dersi (her projede geçerli) | `playbook/` | — |
| Atlanamaz kural | `standards/` + bir **gate** | — |
| Mimari karar (metodoloji) | `governance/decisions/` | — |
| Tekrar kullanılacak script | `scripts/` + playbook referansı | — |
| SAP sistemi, müşteri, paket | — | `project.yaml` · `.conn_adt` · `CLAUDE.md` |
| İş kuralı / sprint kararı | — | `governance/` |
| Pakete özel istisna | — | `<source_root>/<MOD>/<PKG>/.rules.md` |
| Core kuralını bu projede daraltmak | — | `playbook-local/` · `standards-local/` · `validators-local/` |

Karar ağacı: [`CLAUDE.core.md`](CLAUDE.core.md) §4 **SORU 0**.

**Akış tek yönlü değildir.** Proje core'a *bakar* (junction, salt-görünüm) — core'a
**yazmaz**. Projede öğrenilen metodoloji dersi buraya **PR ile** geri döner (T1–T11
tetikleri). Merge sonrası makinede tek `git -C C:\IX\DEV_CORE pull` → **tüm projeler**
aynı anda güncellenir. `template_project`'in "Bilinen sapmalar" listesi tam olarak böyle
doğdu: bootstrap provası el kitabındaki 7 boşluğu ortaya çıkardı, hepsi buraya işlendi.

**Genericize kuralı:** bu repo public'tir ve her projeye bakar. `pre_tool_guard` core'a
müşteri/firma adı, SAP host adı, SAP kullanıcı adı, transport numarası ve kişisel handle
yazılmasını **bloklar** — bu bölümü yazarken iki kez bloklandım, kural çalışıyor.
Placeholder kullan: `<SAP_HOST>`, `<PROJECT_NAME>`, `<TRANSPORT>` (`ZSD001` demo paketi
bilinçli istisnadır).

## Kilit dokümanlar

[`CLAUDE.core.md`](CLAUDE.core.md) · [`AGENTS.md`](AGENTS.md) ·
[`ONBOARDING.md`](ONBOARDING.md) · [`MAINTENANCE.md`](MAINTENANCE.md) ·
[`PROJECT_BOOTSTRAP.md`](PROJECT_BOOTSTRAP.md) ·
[`governance/decisions/`](governance/decisions/) (mimari gerekçeler — ADR 0003 katmanlar,
0005 yasaklar, 0006 reviewer, 0007 MCP, 0020 bu mimari)
