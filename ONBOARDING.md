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
| **Kullanıcı-düzeyi ayarlar** (`~/.claude/settings.json`) | Şablonla **ELLE birleştir**: [`claude/user-settings.template.json`](claude/user-settings.template.json) — `permissions.allow/deny` + `defaultMode`. ⚠ Otomatik uygulanmaz. Bu dosya yoksa rutin komutlar sürekli onay sorusu çıkarır ve otonom adımlar yarıda kalır (ölçüldü 2026-09-17: iki makine arasındaki en büyük davranış farkı buydu). ⛔ D32: SAP-yazma/davranış-yüzeyi araçları bu listeye GİRMEZ |
| Claude Code plugin seti | `team_setup` içindeki `setup_plugins.py` kurar (ui5 · playwright-MCP · pyright-lsp · plugin-dev vb.) — makine-düzeyi, clone ile GELMEZ; envanter: [`governance/tooling-plugins.md`](governance/tooling-plugins.md) |

## 0a. KURULUM KAPSAMI — hangi yüzeyi KİM üretir (klonla GELMEYENLER)

> Bir kurulum *"aynı çalışmıyor"* dediğinde sorun neredeyse her zaman bu tablodadır: repo
> klonu yalnız **ilk satırı** getirir, geri kalan her şey makine-lokaldir. Tablo, iki makine
> arasında ölçülen farklardan türetilmiştir (2026-09-17, `parity_probe`).

| Yüzey | Nerede yaşar | Kim üretir | Nasıl doğrulanır | Klonla gelir mi |
|---|---|---|---|---|
| Çekirdek metodoloji (`core/**`) | çekirdek klonu | `git clone` | `git -C core log -1` | ✅ |
| Junction'lar (`core`, `.claude/agents\|skills\|commands`) | proje | `team_setup.py` | `ix_doctor` K1/K4 | ❌ |
| Çekirdek fiziksel kopyası `.claude/rules/00-claude-core.md` | proje | `team_setup` (claude_overlay) | `session_start` **[YUKLEME]** satırı (Q286) | ❌ |
| `.claude/settings.json` · `scripts/hook_shim.py` | proje | `team_setup.dosya_tamamla()` | `session_start` D7 drift | ❌ |
| `.claude/active_package` | proje | `team_setup.dosya_tamamla()` → `project.yaml`'dan türetir | `parity_probe` → `aktif_paket_drift` | ❌ |
| auto-memory (dersler) | kullanıcı profili `~/.claude/projects/<slug>/memory/` | `seed_memory.py` | `parity_probe` → `memory.ders_sayisi` | ❌ |
| **Kullanıcı-düzeyi ayarlar** (`permissions`, `defaultMode`) | `~/.claude/settings.json` | **ELLE** — `claude/user-settings.template.json` ile birleştir | `parity_probe` → `mcp_ve_profil` | ❌ |
| SAP bağlantısı `.conn_adt` | proje kökü | **KULLANICI** (şifreyi kendisi yazar — sohbete YAZILMAZ) | MCP `ping` · `ix_doctor` | ❌ |
| CLI'lar: `claude` · `gh` · `node`/`npm` · `python` | makine | installer/winget (`winget install --id GitHub.cli -e`) | `ix_doctor` K3 | ❌ |
| Claude Code plugin seti (ui5 · playwright-MCP · pyright-lsp …) | makine | `team_setup` → `setup_plugins.py` | [`governance/tooling-plugins.md`](governance/tooling-plugins.md) | ❌ |
| git **global** baseline (`autocrlf`/`longpaths`/`defaultBranch`) | makine | elle `git config --global` | `ix_doctor` K2 · `parity_probe` → `yol_hijyeni` | ❌ |
| `.playwright*/` çıktı klasörleri (erişilebilirlik dökümü, log) | proje | **aracın kendisi**, ilk koşumda | gitignore'ludur; **prosedür gerekmez** — gereken *araç* zaten plugin setinde | ❌ (gerekmez) |

⚠ **"Klonla gelir mi ❌" olan her satır, yeni makinede TEKRAR yapılır.** Biri atlanırsa
kurulum çalışır **görünür** ama farklı davranır — en sık atlananlar: kullanıcı-düzeyi
ayarlar, `gh`, memory tohumu.

> ⭐ **Çekirdek GÜNCELLEMESİ** (ilk kurulum değil) ayrı ve kanonik bir prosedürdür:
> [`playbook/howto-cekirdek-guncelleme.md`](playbook/howto-cekirdek-guncelleme.md) — slash komutu
> `/core-guncelle`. Bu tablo onun 5. adımının (makine-lokal yüzeyler) referansıdır.

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
Alan şablonu: [`claude/conn_adt.template`](claude/conn_adt.template) (tek sistem; çoklu-tier: proje `conn/*.env` — ADR 0010).

## 3. Çalışma kökü modeli + FREEZE

- **Çalışma kökü = `C:\IX`** — DEV_CORE + tüm proje clone'ları bu kökün altındadır.
- **Eski dünya = `<FROZEN_ROOT>` = dondurulmuş SALT-OKUNUR arşiv.** Okuma serbest;
  yazma/commit/push/checkout YASAK. Eski GitHub org'undaki yedek repolar da aynı
  statüdedir (push almaz).
  ⚠ **Bu kuralı hiçbir runtime guard ZORLAMIYOR.** `pre_tool_guard` R10 freeze-guard'ı
  ve `project.yaml frozen_readonly_paths` anahtarı **2026-07-10'da KALDIRILDI** (fiil-kara
  listesi 6 yoldan sızıyordu — dd · install · git clean · git checkout · heredoc-redirect ·
  PS değişkeni; koruma OS izniyle yapılır, komut-metni regex'iyle değil). Negatif testle
  doğrulandı: dondurulmuş köke `Write`/`Bash` → **exit 0 (serbest)**. Kural = disiplin;
  gerçek koruma istiyorsan klasöre **Windows salt-okunur/ACL** izni ver.

## 4. ⚠️ SİLME MATRİSİ — junction'lar ve tehlikeli komutlar

Junction bir "klasör görünümlü bağlantı"dır; hedefi (DEV_CORE) TEK fiziksel kopyadır.

| İşlem | Kural |
|---|---|
| Junction'a `rm -rf` / `Remove-Item -Recurse -Force` / `git clean` / `rimraf` / `rmdir /S` | **ASLA.** Özyinelemeli silme junction İÇİNE inip **hedefi (canlı çekirdeği) silebilir** — davranış toolchain-sürümüne bağlıdır (güncel git/PS'te link-sınırında durduğu test edildi; eski PS build'leri, `rimraf`, `robocopy /MIR`, eski `shutil.rmtree` TEST EDİLMEDİ). ⚠ **Seni durduran bir guard YOK:** `pre_tool_guard` R9 özyinelemeli-silme bloğu **2026-07-10'da KALDIRILDI** (bloklanan `rm -rf` yerine aynı dizin `shutil.rmtree` ile silindi → guard aracı değiştirtti, sonucu değil; ayrıca junction silme geri alınabilir: `team_setup.py --repair-junctions`). Negatif test: `rm -rf <proje>/core` ve `Remove-Item -Recurse core` → **exit 0**. Kural sende. |
| Junction'ı KALDIRMAK gerekiyorsa | Yalnız **`rmdir <yol>`** (cmd, `/S` YOK) — sadece bağlantıyı söker, hedefe dokunmaz. |
| Junction (yalnız link) silindiyse | Proje çalışmaz hale gelir (loader/hook/skill kaybı) → onarım: `team_setup.py --repair-junctions`. |
| `<FROZEN_ROOT>` altına yazma | **Runtime guard YOK** (R10 2026-07-10'da kaldırıldı, bkz. §3) — koruma = disiplin kuralı; kalıcı koruma istenirse OS/ACL. |

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

## 7. İlk oturum: çekirdek yükleniyor mu — beyana değil SATIRA bak (D18 → Q286)

Proje `CLAUDE.md`'si çekirdeği artık **import ETMEZ** (Q286, 2026-09-12). Eski
`@core/CLAUDE.core.md` import'u `core/` junction'ı ardında kaldığı için harness'ta **dış
import** sayılıyor, onay bayrağı kapalıyken **sessizce yüklenmiyordu** (2026-08-20'den beri,
belirti vermeden). Çekirdek bugün `team_setup.py`'nin ürettiği **fiziksel kopya**
`.claude/rules/00-claude-core.md` olarak yüklenir — onay diyaloğu yoktur.
Kanarya: `session_start`'ın `[YUKLEME — session_start]` satırı (`ÖN KOŞUL: TAMAM|EKSİK …` +
`ÖNCEKİ OTURUM <sid8>: core=YÜKLENDİ|YÜKLENMEDİ|ÖLÇÜLEMEDİ`). `EKSİK` ya da `YÜKLENMEDİ`
görürsen: `python C:\IX\DEV_CORE\scripts\team_setup.py --repair-junctions`; proje
`CLAUDE.md`'sinde eski `@core/...` satırı kaldıysa sil. Emin değilsen liderden yardım iste.

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

### 9.1 İki makine arasında EŞLİK ölçümü: `parity_probe`

```powershell
python core/scripts/parity_probe.py             # --no-doctor (hızlı/ağsız) · --anon (maskeli)
```

**Ne zaman:** *"aynı çekirdeği klonladım ama diğer makinede Claude tam aynı çalışmıyor"* şüphesi.
`ix_doctor` **tek makinenin** sağlığını sorar (FAIL var mı); `parity_probe` **iki makineyi
karşılaştırır** — aynı enstrüman iki vakada koşulur, JSON'lar diff'lenir (kontrol grubu, PATTERN #19).

Ölçtüğü yüzey, özellikle **klonla GELMEYEN** katmanlar: harness (Claude Code sürümü · `model` ·
`autoMode` · plugin) · `.claude/rules/00-claude-core.md` **fiziksel kopyası** (Q286 — izlenmiyor,
yalnız `team_setup` overlay'i üretir) · kanca envanteri ↔ `settings.template.json` farkı ·
junction'lar + `core` dal/HEAD/gerilik · **auto-memory** (ders sayısı, tip dağılımı, tohumlanmamış
seed listesi) · MCP/profil · `ix_doctor` 7 katman + `run_all_validators --quick` sonucu.

Kurallar: **salt-okunur** (hiçbir proje/core dosyasına yazmaz, SAP'ye bağlanmaz) · raporu
**sistem temp**'ine yazar, proje kökünü kirletmez · `.conn_adt` ve izin listesi **içeriği** rapora
girmez (yalnız var-mı + sayım), `--anon` kullanıcı adı/host maskeler · eksik kaynakta
*"fark YOK"* demez, **`OLCULEMEDI`** yazar (ölçülemedi ≠ temiz — `CLAUDE.core.md` §7 kapsam beyanı).

## 10. Çalışma düzeni — bilmen gereken minimum

- **Git modeli (L1, [`AGENTS.md`](AGENTS.md) §1):** tek uzun-yaşayan branch = `main`;
  `main` doğrudan-push'a KAPALI → her değişiklik **kısa-ömürlü branch + PR + CI** ile girer;
  merge sonrası branch silinir. Merge = lider/kullanıcı onayı; push öncesi HER ZAMAN
  kullanıcı onayı; `--force`/`--no-verify` yok. **FREEZE:** dondurulmuş arşiv köklerine
  git dahil yazma YOK — **disiplin kuralı, guard yok** (§3).
- **Core'a yazma:** herkes PR + CI required-check (lider dahil) — [`MAINTENANCE.md`](MAINTENANCE.md).
  Genericize-on-write: core'a proje/müşteri kimliği GİREMEZ (pre-commit gate + CI tarar).
- **Core kırıldıysa:** `git -C core checkout stable` (proje kökünden; core bir junction'dır) → bilinen-iyiye dönüş;
  onarım sonrası `git switch main`. Junction'a dokunulmaz.
- **Core pull:** makinede TEK yerden — `git -C core pull` — proje kökünden çalışır ve **sabit sürücü/klasör varsayımı taşımaz** (D24). ⚠ Dokümanda gördüğün `C:\IX\...` biçimi bir örnektir, kural değil; `session_start` "origin'in gerisindesin" uyarır).
- **Çekirdekte bir şeyi değiştirmen gerekirse ve upstream'e yazma yetkin YOKSA:** DUR — önce kusurun kurulumda mı çekirdekte mi olduğunu ölç, sonra **yalnız Issue** aç (kanıt formatı zorunlu; fork + PR yolu yok — düzeltme fikri Issue'nun `ÖNERİ` bölümüne): [`playbook/howto-cekirdek-bulgu-bildirimi.md`](playbook/howto-cekirdek-bulgu-bildirimi.md) · [`MAINTENANCE.md`](MAINTENANCE.md) §6b. Lokal yama meşrudur ama **kendi dalında** ve görünür olmalı.
- **⛔ KESİN YASAKLAR (ADR 0005)** her projenin kök `CLAUDE.md`'sine fiziksel damgalıdır;
  SAP işlemleri playbook-önce disiplinine tabidir ([`AGENTS.md`](AGENTS.md) §6).

## 11. Hızlı kontrol listesi (yeni makine)

- [ ] §0 ön-koşullar (python/git-baseline/node/claude/gh/plugin)
- [ ] `C:\IX\DEV_CORE` clone (bir kez) + proje clone
- [ ] `team_setup.py` → 4 junction + bağımlılıklar + seed OK
- [ ] `.conn_adt` KENDİ kimliğinle (şifre sohbete yazılmaz)
- [ ] İlk oturum: @import onayı VER (Decline KALICI — §7) + MCP `sap-adt` onayı
- [ ] Ekran-teyidi formatı geliyor mu (gelmiyorsa §7 + `--repair-junctions`)
- [ ] `~/.claude/settings.json` ← `claude/user-settings.template.json` ile **elle birleştirildi** (§0)
- [ ] `.claude/active_package` var (yoksa `team_setup` yeniden koş) — §0a
- [ ] memory tohumu: `python core/scripts/seed_memory.py --dry-run` → eklenecek 0 ya da bilinçli
- [ ] `python core/scripts/ix_doctor.py` → FAIL yok
- [ ] (ikinci makine varsa) `python core/scripts/parity_probe.py` → iki raporu karşılaştır (§9.1)
- [ ] OneDrive/sync kapsamında `C:\IX` YOK (§5)
- [ ] Yabancı projeye temas edeceksen §8 protokolünü ezberle

> Proje-özel değerler (SAP sistemi, aktif paket, dondurulmuş kök yolları) bu dokümanda
> YOKTUR — her projenin kendi `ONBOARDING.md` yaması + `CLAUDE.md`'sindedir.
