# PROJECT_BOOTSTRAP — Yeni Proje Açılışı (STEP 0–6)

> **Temel ilke:** Yeni proje metodolojiyi **EDİNMEZ** (kopyalamaz) — junction ile core'a
> **BAKAR** (ADR 0020). Projeye kurulan şey = ince iskelet + bağlantılar. Hedef süre:
> **~30–60 dk** (STEP 0 kararları hazırsa). Aşağıda `XYZ` örnek proje adıdır.

## Ön koşul — STEP 0 öncesi (makinede ZATEN var; proje başına TEKRARLANMAZ)

`C:\IX\DEV_CORE\` clone'u makinede BİR KEZ durur. Yeni proje için DEV_CORE'a hiçbir şey
yapılmaz: ne clone, ne kopya, ne branch. Tüm projeler **aynı tek fiziksel DEV_CORE'a**
bakar — core'a düşen her düzeltme hepsine anında yansır.
Makine ön-koşulları (Python/git/Node/Claude CLI): [`README.md`](README.md) "Kurulum".

## STEP 0 — Ön-kararlar (5 dk, kod yok; cevaplanmadan STEP 1'e geçilmez)

| Karar | Nereye girecek |
|---|---|
| **Repo gerekli mi? (K13):** `full` (GitHub) / `local` (yalnız lokal git — kısa projede ÖNERİLEN) / `none` (git'siz) | STEP 1 (`local`/`none` → STEP 1 ATLANIR) + `project.yaml repo_mode` |
| **SAP profili ne? (İLK teknik karar):** `ecc / s4_private / s4_public / btp_abap` + release + (ecc ise) db + (s4_private ise) cleancore_policy + master_language | `project.yaml` (STEP 4) — tüm kural rejimini bu belirler (profiles/) |
| SAP sistemi hangisi? (host/client/user; ayrı sistem mi) | `.conn_adt` (STEP 4) |
| Kaynak-kod klasör adı? (K12; varsayılan `SOURCE_CODES`) | `init_project --source-root` + `project.yaml source_root` |
| Paket prefix'leri + modüller ne? | `project.yaml` (STEP 4) + ilk paket adı (STEP 6) |
| Repo adı + ekip/yetki? (yalnız `full`) | STEP 1 GitHub ayarı |

### LITE akış (K13 — repo_mode=`local`|`none`; STEP 1 ATLANIR)

`local` → `mkdir C:\IX\XYZ ; git -C C:\IX\XYZ init` (remote yok;
tarihçe+geri-alma kalır). `none` → sadece `mkdir C:\IX\XYZ` (git yok; gün-sonu push
disiplini yoktur, kalıcılaştırma kullanıcı takdirindedir; `check_core_not_committed`
otomatik SKIP olur). Junction/core-canlılık/memory/profil mekanizmalarının HİÇBİRİ
git'e bağımlı değildir — çekirdek değer repo'suz da tam çalışır.
Sonraki adımlar aynıdır: STEP 2'de `--repo-mode local|none` ver; STEP 5/6'daki
git/push kalemleri düşer.

## STEP 1 — Repo + lokal klasör *(yalnız repo_mode=full; LITE modlarda ATLA)*

```powershell
gh repo create <ORG>/XYZ --private
git clone https://github.com/<ORG>/XYZ.git C:\IX\XYZ
```

**Koruma kurulumu + ilk-push istisnası:** yeni repoda `main-pr-required` ruleset'i ve CI
workflow'u kurulup **AKTİF edilene dek** main'e doğrudan push mümkündür — bilinçli sıra:
ruleset'i önce **DISABLED** durumda yarat → iskelet ilk push'u yap (STEP 6) → ruleset'i
**ACTIVE** et. Aktifleşince main doğrudan-push'a kapanır; her sonraki değişiklik
kısa-branch + PR + CI ile girer ([`AGENTS.md`](AGENTS.md) §1).

## STEP 2 — `init_project.py` → iskeleti ÜRETİR (kopyalamaz)

```powershell
python C:\IX\DEV_CORE\scripts\init_project.py C:\IX\XYZ --name XYZ --repo-mode full
#  --repo-mode full|local|none (K13; STEP 0 kararı — LITE akışta local|none)
#  --source-root SOURCE_CODES (varsayılan) · --force (var olanın üstüne)
```

| Üretilen | Kaynak / içerik |
|---|---|
| `CLAUDE.md` (ince) | `claude/CLAUDE.project.template.md`'den: `@core/CLAUDE.core.md` import + boş proje bölümü |
| `.claude/settings.json` | `claude/settings.template.json`'dan; hook'lar proje-lokal `scripts/hook_shim.py` üzerinden core'a gider |
| `scripts/hook_shim.py` | `claude/hook_shim.template.py`'den (runpy; kopuk-junction'da NET onarım mesajı) |
| `.gitignore` | Sızıntı kilidi HAZIR: `/core/`, `.claude/agents|skills|commands/` + standart ignore'lar |
| `.gitattributes` | CRLF/binary normalizasyon kararı (py/sh/yaml/json = LF; görsel/pdf/zip = binary) |
| `.mcp.json` | İnce; MCP server core'dan (`PYTHONPATH=core`), bağlantı proje kökündeki `.conn_adt`'den |
| `project.yaml` | Şablon (repo_mode/source_root dolu gelir; kalanı STEP 4) |
| `<source_root>/`, `conn/`, `governance/`, `playbook-local/`, `standards-local/`, `scripts/validators-local/` | Boş overlay/proje klasörleri (governance = proje ADR/registry evi) |

## STEP 3 — `team_setup.py` → junction'lar + memory seed

```powershell
cd C:\IX\XYZ
python C:\IX\DEV_CORE\scripts\team_setup.py
```

(a) DEV_CORE clone kontrolü; (b) **4 junction** (`mklink /J` — admin gerektirmez):

```
C:\IX\XYZ\core             ══► C:\IX\DEV_CORE
C:\IX\XYZ\.claude\agents   ══► C:\IX\DEV_CORE\claude\agents
C:\IX\XYZ\.claude\skills   ══► C:\IX\DEV_CORE\claude\skills
C:\IX\XYZ\.claude\commands ══► C:\IX\DEV_CORE\claude\commands
```

(c) core hooksPath (DEV_CORE reposunda pre-commit gate'leri); (d) pip bağımlılıkları +
Claude Code plugin'leri + npm CLI'ler (makine-düzeyi; NON-FATAL — FE işinden önce tamam
olmalı); (e) `seed_memory` → core memory-seed'den projenin memory'sini tohumlar
(memory proje-YOL bazlıdır; yeni proje sıfır memory ile başlar — seed bu açığı kapatır);
(f) smoke testler. Onarım: `--repair-junctions` · worktree: `--provision-worktree <yol>`.

> **"Skill/script/agent klasörde nasıl oluşacak?" — OLUŞMAZ.** Junction sayesinde proje
> içinden `core\scripts\...`, `.claude\skills\...` olarak GÖRÜNÜRLER; diskte tek kopya
> vardır ve o kopya DEV_CORE'dur.

## STEP 4 — Proje-özel değerleri elle doldur (STEP 0 kararlarından)

- `.conn_adt` → projenin SAP sistemi (host/client/user; **proje-içi durur — K10**).
  Alan şablonu: [`claude/conn_adt.template`](claude/conn_adt.template) (çoklu-tier:
  proje `conn/*.env` + `switch_tier.py` — ADR 0010)
- `project.yaml` → `sap_profile` + `release` (+ `db`/`cleancore_policy`) +
  `master_language` + paket prefix'leri + iş-anahtarları. Tam anahtar kataloğu:
  [`MAINTENANCE.md`](MAINTENANCE.md) §"project.yaml kataloğu".
- `CLAUDE.md` proje bölümü → SAP bağlantı satırı, proje-özel notlar

## STEP 5 — KABUL GATE'İ (geçmeden projede İŞ YAPILMAZ)

| # | Kanıt | Nasıl |
|---|---|---|
| 1 | Loader + hook'lar çalışıyor | Projede oturum aç → **ekran teyidi formatı geliyor** (= `@core` import + session_start junction üzerinden OK) |
| 2 | MCP kendi sistemine bağlı | `ping` + read-only `adt_get` → PROJENİN SAP sistemi (başka projeninki DEĞİL) |
| 3 | Validators PASS | `python core/scripts/validators/run_all_validators.py` (core + varsa local) |
| 4 | Sızıntı kilidi çalışıyor | `git status` → core içeriği görünMÜyor; `git ls-files core/ .claude/agents` → boş *(repo_mode=none: SKIP)* |
| 5 | Kurulum sağlığı | `python core/scripts/ix_doctor.py` → FAIL yok (7-katman tarama) |

## STEP 6 — İlk paket + ilk commit

```powershell
python core/scripts/bootstrap_package.py <PKG_FULL> --title "..."
git add -A ; git commit -m "chore(bootstrap): XYZ proje iskeleti (PROJECT_BOOTSTRAP)"
git push -u origin main   # yalnız repo_mode=full (ilk-push istisnası: STEP 1)
```

> **NOT:** `main-pr-required` ruleset'i **ACTIVE** edildikten sonra (STEP 1) main'e
> doğrudan push KAPANIR → bu ilk push'tan sonraki her değişiklik kısa-ömürlü branch +
> PR + CI ile girer ([`AGENTS.md`](AGENTS.md) §1). `repo_mode=local`'da push satırı,
> `repo_mode=none`'da tüm git satırları düşer (LITE akış).

Uzak repoda metodolojiden TEK SATIR görünmez — sadece iskelet + proje içeriği.

## Paralellik — birden çok proje aynı anda

- Her oturumun cwd'si kendi proje kökü → hook'lar `CLAUDE_PROJECT_DIR` ile KENDİ
  projesini, MCP KENDİ `.conn_adt`'sini görür. Çakışma yok.
- Bir oturumda core'a yazılan ders diğer projede ANINDA görünür (aynı fiziksel dosya).
  Başka makine/PR'dan gelen core değişikliği: makinede tek `git -C C:\IX\DEV_CORE pull`
  → tüm projeler birden güncellenir (session_start "core origin'in gerisinde" uyarır).

## Sorun giderme

| Belirti | Çözüm |
|---|---|
| Hook "CORE JUNCTION KOPUK" diyor | `python C:\IX\DEV_CORE\scripts\team_setup.py --repair-junctions` |
| Ekran teyidi gelmiyor | `CLAUDE.md` içindeki `@core/CLAUDE.core.md` import'u + `core` junction'ını kontrol et |
| MCP yanlış sisteme bağlı | Proje kökündeki `.conn_adt`'yi kontrol et (env `ADT_SAP_*` override eder — D17) |
| Validators "CORE-modu" diyor (proje-modu beklerken) | `project.yaml` proje kökünde mi + `sap_profile` dolu mu |
