# ONBOARDING — Yeni Geliştirici / Yeni Makine El Kitabı

> **Kime:** Canlı-çekirdek (DEV_CORE) düzenine ilk kez katılan geliştirici — veya mevcut
> geliştiricinin YENİ makinesi. **Ne:** Kurulumdan ilk güvenli oturuma kadar insan-okur
> rehber. **Otomasyon ikizi:** proje içinde `/onboard` komutu (`claude/commands/onboard.md`)
> adımların çoğunu senin yerine yürütür — bu doküman "neden"i ve elle-yapılacakları anlatır;
> ikisi birbirini tamamlar, çelişmez.
>
> İlişkili: [`README.md`](README.md) (mimari özet) · [`MAINTENANCE.md`](MAINTENANCE.md)
> (core işletimi) · [`PROJECT_BOOTSTRAP.md`](PROJECT_BOOTSTRAP.md) (YENİ proje açılışı —
> bu doküman mevcut projeye katılmayı anlatır).

---

## 0. Ön-koşullar (makine-düzeyi — repo bunları GETİRMEZ)

| Gereksinim | Doğrulama / kurulum |
|---|---|
| Python ≥ 3.10 | `python --version` |
| git + **global baseline** | `git config --global core.autocrlf false` · `git config --global core.longpaths true` · `git config --global init.defaultBranch main` (ix_doctor katman-2 bunları denetler) |
| Node.js + npm | `node --version` (UI5/FE araç zinciri için) |
| Claude Code CLI | `claude --version` |
| GitHub CLI + auth | `gh auth status` (PR/CI akışı + ix_doctor katman-3 için) |
| Claude Code plugin seti | `team_setup` içindeki `setup_plugins.py` kurar (ui5 · playwright-MCP · pyright-lsp · plugin-dev vb.) — makine-düzeyi, clone ile GELMEZ; envanter: [`governance/tooling-plugins.md`](governance/tooling-plugins.md) |

## 1. Mimari: canlı çekirdek + junction (NEDEN böyle — ADR 0020)

Metodoloji (standartlar, playbook, script/validator/hook, MCP server, agent/skill
tanımları) **tek fiziksel kopyadır**: `C:\IX\DEV_CORE`. Projeler bu kopyaya **junction**
ile bakar — kopyalamaz, port etmez. Core'a düşen bir düzeltme aynı makinedeki TÜM
projelere ANINDA yansır; "hangi projede hangi sürüm var" sorusu yoktur.
Gerekçe + reddedilen alternatifler: [`governance/decisions/0020-canli-cekirdek-junction-mimarisi.md`](governance/decisions/0020-canli-cekirdek-junction-mimarisi.md).

**4 junction haritası** (proje başına; `mklink /J` — admin/dev-mode GEREKTİRMEZ):

```
C:\IX\<PROJECT_NAME>\core             ══► C:\IX\DEV_CORE
C:\IX\<PROJECT_NAME>\.claude\agents   ══► C:\IX\DEV_CORE\claude\agents
C:\IX\<PROJECT_NAME>\.claude\skills   ══► C:\IX\DEV_CORE\claude\skills
C:\IX\<PROJECT_NAME>\.claude\commands ══► C:\IX\DEV_CORE\claude\commands
```

Proje reposuna core içeriği ASLA commit'lenmez — `.gitignore` + `check_core_not_committed`
validator'ı + pre_tool_guard commit-kapsam kontrolü + CI bunu kilitler.

## 2. Kurulum (mevcut projeye katılım — 3 komut)

```powershell
git clone https://github.com/<ORG>/DEV_CORE.git C:\IX\DEV_CORE      # makinede BİR KEZ
git clone https://github.com/<ORG>/<PROJECT_REPO>.git C:\IX\<PROJECT_NAME>
cd C:\IX\<PROJECT_NAME>
python C:\IX\DEV_CORE\scripts\team_setup.py
```

`team_setup.py` idempotenttir (eksik olanı tamamlar): 4 junction + core hooksPath +
pip bağımlılıkları + Claude Code plugin'leri + npm CLI'ler + memory-seed + smoke testler.
Kopuk junction onarımı: `python C:\IX\DEV_CORE\scripts\team_setup.py --repair-junctions`.

Sonra **kişisel** dosyanı yarat: proje kökünde `.conn_adt` (SAP host/client/KENDİ
kullanıcın — gitignore'da, repoya gitmez; şablon: proje `conn/` klasörü). Şifreyi Claude
sohbetine YAZMA — dosyayı kendin düzenle.

## 3. Çalışma kökü modeli + FREEZE

- **Çalışma kökü = `C:\IX`** — DEV_CORE + tüm proje clone'ları bu kökün altındadır.
- **Eski dünya = `<FROZEN_ROOT>` = dondurulmuş SALT-OKUNUR arşiv.** Okuma serbest;
  yazma/commit/push/checkout YASAK — `project.yaml frozen_readonly_paths` üzerinden
  **pre_tool_guard R10 (freeze-guard)** her Edit/Write/Bash yazma teşebbüsünü RED eder.
  Eski GitHub org'undaki yedek repolar da aynı statüdedir (push almaz).

## 4. ⚠️ SİLME MATRİSİ — junction'lar ve tehlikeli komutlar

Junction bir "klasör görünümlü bağlantı"dır; hedefi (DEV_CORE) TEK fiziksel kopyadır.

| İşlem | Kural |
|---|---|
| Junction'a `rm -rf` / `Remove-Item -Recurse -Force` / `git clean` / `rimraf` / `rmdir /S` | **ASLA.** Özyinelemeli silme junction İÇİNE inip **hedefi (canlı çekirdeği) silebilir** — davranış toolchain-sürümüne bağlıdır (güncel git/PS'te link-sınırında durduğu test edildi; eski PS build'leri, `rimraf`, `robocopy /MIR`, eski `shutil.rmtree` TEST EDİLMEDİ). **pre_tool_guard R9** core/junction path'ine dokunan HER özyinelemeli silmeyi bloklar — bu sigortayı kapatmaya çalışma. |
| Junction'ı KALDIRMAK gerekiyorsa | Yalnız **`rmdir <yol>`** (cmd, `/S` YOK) — sadece bağlantıyı söker, hedefe dokunmaz. |
| Junction (yalnız link) silindiyse | Proje çalışmaz hale gelir (loader/hook/skill kaybı) → onarım: `team_setup.py --repair-junctions`. |
| `<FROZEN_ROOT>` altına yazma | **R10** bloklar (bkz. §3). |

## 5. OneDrive / yedekleme yazılımı uyarısı

Çalışma kökü (`C:\IX`) **hiçbir senkron/yedekleme yazılımının (OneDrive, Dropbox, vb.)
kapsamına ALINMAZ.** Junction'a alışkın olmayan sync araçları döngüye girebilir veya tek
fiziksel içeriği çoklayıp çakışma üretebilir. Yedekleme ihtiyacını git zaten karşılar
(uzak repo + `stable` tag).

## 6. Multi-root workspace + arama görünürlüğü (D29)

- Editörde **proje kökü + `C:\IX\DEV_CORE`'u birlikte** aç (multi-root workspace) —
  metodolojiyi doğrudan görüp düzenlersin (core değişikliği yine PR ile girer).
- **Arama tuzağı (D29):** Claude'un Grep aracı `.gitignore`'a uyar ve `core/` proje
  tarafında ignore'ludur → proje kökünden yapılan arama metodolojiyi GÖRMEZ. Metodoloji
  araması DAİMA `path=core/...` ile yapılır; **kökten sıfır-sonuç ≠ "core'da yok".**

## 7. İlk oturum: @import onay diyaloğu — Decline'a BASMA (D18)

Proje `CLAUDE.md`'si çekirdeği `@core/CLAUDE.core.md` ile import eder. İlk oturumda
Claude Code bu import için **onay diyaloğu** çıkarabilir. **Decline KALICIDIR**: diyalog
bir daha çıkmaz, import sessizce devre dışı kalır → loader/yasaklar/protokol yüklenmez.
Belirti (kanarya): oturum ilk yanıtı **"Ekran Teyidi" formatıyla başlamıyor**
(bkz. [`CLAUDE.core.md`](CLAUDE.core.md) §3). Kazara Decline'ladıysan proje güven
ayarlarını sıfırlayıp import'u yeniden onayla; emin değilsen liderden yardım iste.

## 8. S2 — MİSAFİR MODU: yabancı projeye ilk temas (§11.3-F3)

Tanımadığın/metodolojisiz bir klasörü Claude ile açmak = oradaki hook/MCP/CLAUDE.md'nin
**onaysız çalışması** demektir (hook = keyfi komut). Protokol — sırası BAĞLAYICI:

1. **ÖNCE Claude'suz pre-scan:** `python C:\IX\DEV_CORE\scripts\foreign_project_audit.py <yol>`
   (dosya-varlık envanteri + risk sınıfı; `--deep` = hook/MCP komutlarını ve import
   satırlarını listeler — yine Claude'suz, yalnız okur).
2. **İlk oturum yalnız `claude --safe-mode`** ile açılır.
3. `python C:\IX\DEV_CORE\scripts\guest_mode.py <yol>` → hedefe `CLAUDE.local.md` üretir
   (ADR 0005 yasaklar + TAHMİN-YASAK + çelişkide-DUR, oturum-yerel).
4. **Kod-sınıfı yüzey (hooks / MCP / settings) insan gözüyle incelenmeden NORMAL oturum
   AÇILMAZ.** Değerli dış kural → `intake/` karantinası → çakışma-analizi → PR (§8 firewall,
   [`CLAUDE.core.md`](CLAUDE.core.md)).

## 9. Kurulum doğrulama: `ix_doctor`

```powershell
python core/scripts/ix_doctor.py            # proje kökünden; --layer N / --live-sap / --json
```

`ix_doctor` = kurulumun uçtan-uca sağlık taraması (sap_doctor'un kardeşi: o "SAP bağlantısı
sağlıklı mı"ya, bu "canlı-çekirdek kurulumu sağlıklı mı"ya bakar). **7 katman** — FS+bağımlılık
(4 junction + plugin/CLI), git (baseline + stable), GitHub-enforce (ruleset/CI/sızıntı),
Claude-katmanı (settings/shim drift + hook smoke + freeze-guard canlı test), MCP/SAP,
validator+performans, iş-akışı smoke — her kontrol kanıt-satırı basar; exit 0 = FAIL yok.
Tamamlayıcı: `python core/scripts/validators/run_all_validators.py` (proje kökünden).

## 10. Çalışma düzeni — bilmen gereken minimum

- **Git modeli (L1, [`AGENTS.md`](AGENTS.md) §1):** tek uzun-yaşayan branch = `main`;
  `main` doğrudan-push'a KAPALI → her değişiklik **kısa-ömürlü branch + PR + CI** ile girer;
  merge sonrası branch silinir. Merge = lider/kullanıcı onayı; push öncesi HER ZAMAN
  kullanıcı onayı; `--force`/`--no-verify` yok. **FREEZE:** `frozen_readonly_paths`
  köklerine git dahil yazma YOK (R10).
- **Core'a yazma:** herkes PR + CI required-check (lider dahil) — [`MAINTENANCE.md`](MAINTENANCE.md).
  Genericize-on-write: core'a proje/müşteri kimliği GİREMEZ (pre-commit gate + CI tarar).
- **Core kırıldıysa:** `git -C C:\IX\DEV_CORE checkout stable` → bilinen-iyiye dönüş;
  onarım sonrası `git switch main`. Junction'a dokunulmaz.
- **Core pull:** makinede TEK yerden — `git -C C:\IX\DEV_CORE pull` (projelerde core pull
  yoktur; `session_start` "origin'in gerisindesin" uyarır).
- **⛔ KESİN YASAKLAR (ADR 0005)** her projenin kök `CLAUDE.md`'sine fiziksel damgalıdır;
  SAP işlemleri playbook-önce disiplinine tabidir ([`AGENTS.md`](AGENTS.md) §6).

## 11. Hızlı kontrol listesi (yeni makine)

- [ ] §0 ön-koşullar (python/git-baseline/node/claude/gh/plugin)
- [ ] `C:\IX\DEV_CORE` clone (bir kez) + proje clone
- [ ] `team_setup.py` → 4 junction + bağımlılıklar + seed OK
- [ ] `.conn_adt` KENDİ kimliğinle (şifre sohbete yazılmaz)
- [ ] İlk oturum: @import onayı VER (Decline KALICI — §7) + MCP `sap-adt` onayı
- [ ] Ekran-teyidi formatı geliyor mu (gelmiyorsa §7 + `--repair-junctions`)
- [ ] `python core/scripts/ix_doctor.py` → FAIL yok
- [ ] OneDrive/sync kapsamında `C:\IX` YOK (§5)
- [ ] Yabancı projeye temas edeceksen §8 protokolünü ezberle

> Proje-özel değerler (SAP sistemi, aktif paket, dondurulmuş kök yolları) bu dokümanda
> YOKTUR — her projenin kendi `ONBOARDING.md` yaması + `CLAUDE.md`'sindedir.
