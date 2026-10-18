# DEV_CORE — Canlı Metodoloji Çekirdeği

> **Tek cümlede:** Tüm projelerin ORTAK ve CANLI kullandığı
> SAP-AI geliştirme metodolojisi: standartlar, playbook, script/validator/hook takımı,
> MCP server, agent tanımları ve skill'ler — **tek kaynak-gerçek, kopya YOK**.

## 🚀 Kurulum ve güncelleme — Claude Code'a bu prompt'u verin

**Yeni makine / ilk kurulum.** Claude Code'u kurulumu yapacağınız klasörde açın (ör. `C:\IX`),
köşeli parantezleri doldurun ve aşağıdaki metni **olduğu gibi** yapıştırın:

```text
DEV_CORE kurulumunu yap.
Hedef klasör: [C:\IX]
Proje repoları: [https://github.com/<ORG>/<PROJE>.git — birden çok olabilir · yeni proje açacaksam "yeni proje: <AD>" · yoksa "yok"]

1) https://github.com/ix-works/DEV_CORE.git reposunu <hedef klasör>\DEV_CORE altına klonla
   (klasör zaten varsa klonlama, dokunma).
2) <hedef klasör>\DEV_CORE\ONBOARDING.md dosyasındaki "2A. Claude ile kurulum" bölümünü oku ve
   adımlarını SIRAYLA uygula. Dosyada olmayan adım ekleme, kendi bildiğin bir kurulum yolu izleme.
3) Yalnız o bölümün KULLANICI diye işaretlediği adımlarda bana sor; sonunda bölümün istediği raporu ver.
```

**Kurulu makinede güncelleme.** Herhangi bir proje klasöründe Claude Code'u açıp yalnız
`/core-guncelle` yazın — ayrıntı aşağıda, [Güncelleme](#güncelleme-kurulu-makine--core-guncelle).

## Mimari (ADR 0020 — canlı çekirdek + junction)

```
GitHub                                   Lokal disk (her geliştirici)
ix-works/DEV_CORE  ──clone──►  C:\IX\DEV_CORE\        ← BU repo (working tree = canlı çekirdek)
ix-works/<PROJECT_NAME> ─clone─► C:\IX\<PROJECT_NAME>\
                                 ├─ core ══junction══► C:\IX\DEV_CORE
                                 ├─ CLAUDE.md (ince: yasaklar damgası + proje bölümü; @import YOK)
                                 ├─ .claude\rules\ (FİZİKSEL kopya: 00-claude-core.md + claude\rules\*.md)
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
| `CLAUDE.core.md` | Çekirdek loader — yasaklar (ADR 0005), session protokolü, SORU 0, gate tablosu. Projelere import ile DEĞİL, `team_setup`'ın ürettiği fiziksel kopya `.claude/rules/00-claude-core.md` olarak girer (Q286) |
| `AGENTS.md` | **EMEKLİ (SUPERSEDED 2026-08-01, D1)** — otomatik yüklenmez; içeriği `CLAUDE.core.md` §1.1 + `claude/rules/` + `MAINTENANCE.md`'ye taşındı. Tarihçedir, güncel kural kaynağı DEĞİL |
| `claude/rules/` | L1b — dosya-türüne bağlı agent davranışı (SAP kaynak protokolü, UI5, …; `paths:` ile tembel yüklenir) |
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

Adım adım ilk kurulum: yukarıdaki prompt (Claude yürütür) ya da elle [`ONBOARDING.md`](ONBOARDING.md) §2.
`/onboard` komutu bir projede ancak `team_setup` koştuktan sonra görünür (`.claude/commands` bağını
o kurar); kurulum sonrası kontrol + iş özeti içindir.
Yeni PROJE açılışı: [`PROJECT_BOOTSTRAP.md`](PROJECT_BOOTSTRAP.md) (STEP 0–6 + kabul gate'i).
Kurulum doğrulama: `python core/scripts/ix_doctor.py` (proje kökünde; 7-katman sağlık taraması).

## Güncelleme (kurulu makine) — `/core-guncelle`

Çekirdek kurulu bir makinede güncelleme **tek komuttur.** Herhangi bir proje klasöründe Claude
Code'u açıp yaz:

```
/core-guncelle
```

Ek talimat gerekmez. Komut [`playbook/howto-cekirdek-guncelleme.md`](playbook/howto-cekirdek-guncelleme.md)
prosedürünü uçtan uca yürütür: çekirdeği çeker, bu projede ve **aynı makinedeki diğer projelerde**
`team_setup` koşar (junction · kural/ajan kopyaları · ayarlar · memory tohumu), makineye özel
ayarları hizalar, `run_all_validators` + `ix_doctor` ile doğrular ve önce/sonra ölçümünü
(`parity_probe`) proje başına raporlar.

- ⛔ **Yalnız `git pull` YETMEZ** — pull dosyaları getirir; kurulumu hizalamaz, doğrulamaz.
- Bitince **Claude Code'u kapatıp açın.** Yeni oturumun ilk mesajında
  `✓ Yükleme: … core=YÜKLENDİ` satırı görünmelidir.
- **Komut listede yoksa** (çekirdek bu komuttan eski): proje kökünde `git -C core pull` →
  Claude Code'u kapat-aç → `/core-guncelle`.
- **Sonradan kontrol:** proje kökünde `python core/scripts/ix_doctor.py` — FAIL yoksa kurulum
  yapısal olarak sağlamdır (çıktı neye bakmadığını da yazar; Claude'un hangi ajan/kuralı fiilen
  yüklediğini ölçmez). İki makineyi karşılaştırmak: iki tarafta `python core/scripts/parity_probe.py --anon`,
  sonra `--diff A.json B.json`.
- Çekirdekte kusur bulursan ve yazma yetkin yoksa: Issue —
  [`playbook/howto-cekirdek-bulgu-bildirimi.md`](playbook/howto-cekirdek-bulgu-bildirimi.md).

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
  push almaz). Yolları makine-lokaldir ve **disiplin kuralıdır** — runtime guard yok
  (freeze-guard R10 + `frozen_readonly_paths` anahtarı 2026-07-10'da kaldırıldı).

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

[`CLAUDE.core.md`](CLAUDE.core.md) · [`claude/rules/`](claude/rules/) ·
[`ONBOARDING.md`](ONBOARDING.md) · [`playbook/howto-cekirdek-guncelleme.md`](playbook/howto-cekirdek-guncelleme.md) (`/core-guncelle`) ·
[`MAINTENANCE.md`](MAINTENANCE.md) ·
[`PROJECT_BOOTSTRAP.md`](PROJECT_BOOTSTRAP.md) ·
[`governance/decisions/`](governance/decisions/) (mimari gerekçeler — ADR 0003 katmanlar,
0005 yasaklar, 0006 reviewer, 0007 MCP, 0020 bu mimari)
