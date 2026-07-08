# ADR 0020 — Canlı çekirdek (DEV_CORE) + junction çoklu-proje mimarisi

**Durum:** Kabul edildi (2026-07-08; tasarım GECIS-PLAN v3.x, K1–K12 kararlarıyla kapandı)
**Bağlam ADR'leri:** [0003](0003-layered-rule-architecture.md) (L1–L4 katman mimarisi — bu ADR katmanların FİZİKSEL evini belirler) · [0005](0005-sap-standart-obje-koruma-ve-sistem-state-yasaklari.md) (yasaklar; taşınma modeli → [0021](0021-kesin-yasaklar-fiziksel-damga.md)) · [0007](0007-sap-adt-mcp-server.md) (MCP server core'dan yüklenir, bağlantı projeden) · [0019](0019-kural-enforcement-mimarisi-3-eksen-coverage-check.md) (enforcement; buradaki gate'ler o mimariye bağlanır)
**İşletim el kitabı:** [MAINTENANCE.md](../../MAINTENANCE.md) — bu ADR *neden*'i, MAINTENANCE *nasıl*'ı anlatır.

## Sorun

Metodoloji (standards, playbook, scripts/validators/hooks, MCP server, agent/skill
tanımları) birden fazla SAP projesinde ORTAK kullanılmak isteniyor. Önceki model
**template-repo + kopya**ydı: her proje metodolojinin bir kopyasını taşır, iyileştirmeler
batch-port (eski T12 tetikleyicisi) ve `template_drift` taramasıyla elle senkronlanırdı.
Fiilen yaşanan sonuçlar:

- **Kopya-drift:** aynı kuralın proje-kopyası ile template-kopyası ayrışır; hangisi
  kanonik belirsizleşir (CRLF kaynaklı sahte-drift vakası dahi yaşandı — lessons-learned).
- **Senkron yükü:** her ders/pattern için "önce projede yaz, sonra template'e port et"
  çift işi; port kuyruğu (`pending-template-ports`) birikir, unutulur.
- **Ölçeklenmezlik:** ikinci gerçek proje açılırken kopya modeli yükü proje sayısıyla
  çarpar; N proje = N kopya = N drift cephesi.

İstenen: **tek kaynak-gerçek, kopya YOK, aynı makinede anında yansıma** — düzeltme bir
kez yazılır, tüm projeler canlı görür.

## Karar

### 1. Canlı çekirdek + proje-içi junction

- Metodolojinin tamamı tek repoya toplanır: **`DEV_CORE`** (bu repo). Working tree'si
  makinede tek fiziksel kopyadır ve "canlı çekirdek"tir.
- Her proje klasörü core'a **Windows junction**'la bakar (`mklink /J` — admin/dev-mode
  gerektirmez; `team_setup.py` kurar):

```
C:\IX\<PROJE>\core             ══► C:\IX\DEV_CORE
C:\IX\<PROJE>\.claude\agents   ══► C:\IX\DEV_CORE\claude\agents
C:\IX\<PROJE>\.claude\skills   ══► C:\IX\DEV_CORE\claude\skills
C:\IX\<PROJE>\.claude\commands ══► C:\IX\DEV_CORE\claude\commands
```

- Junction path'leri proje `.gitignore`'undadır; core içeriği proje reposuna ASLA
  commit'lenmez (`check_core_not_committed` validator + pre_tool_guard commit-kapsam
  kontrolü + proje-repo CI kilidi — fikri-sermaye sızıntı gate'i, R1).

### 2. İnce proje-CLAUDE.md (loader deseni)

Proje kök `CLAUDE.md`'si incedir: KESİN YASAKLAR fiziksel damgası (ADR 0021) +
`@core/CLAUDE.core.md` import'u + YALNIZ proje-özel bölüm (SAP bağlantısı, aktif paket,
yerel kurallar). Metodoloji proje dosyasına YAZILMAZ — yazım-anı hedef kararı **SORU 0**
([CLAUDE.core.md](../../CLAUDE.core.md) §4): metodoloji → core, proje işi → proje.
Proje-özel genişleme kapıları: `playbook-local/`, `standards-local/`,
`scripts/validators-local/` (core mekanizmaları bunları otomatik keşfeder).

### 3. Hook/settings zinciri + shim

- Hook'lar core'da yaşar; proje `settings.json`'ı `${CLAUDE_PROJECT_DIR}/scripts/hook_shim.py`
  üzerinden çağırır. **Shim** proje reposuna commit'li ~10 satırlık yönlendiricidir
  (D15): junction kopuksa NET hata + onarım komutu basar (kriptik "hook failed" yerine);
  sağlamsa gerçek core hook'unu AYNI süreçte (`runpy`) koşar — subprocess başına +86 ms
  ölçülmüş maliyetten kaçınılır (Ö2).
- DEV_CORE clone'unda `core.hooksPath=scripts/git-hooks` (D19): genericize-leak +
  link-audit + `applies_to` şema gate'leri commit anında koşar; CI aynısını tam-ağaç koşar.
- Mekanizma/değer ayrımı: core script'leri proje-değerlerini **`project.yaml`**'dan okur
  (`source_root`, `sap_profile`, prefix'ler…; katalog: MAINTENANCE §6). Core hiçbir
  proje-değerini hard-code etmez.

### 4. Yazma disiplini: PR + CI + `stable` tag

- `main` branch-protected; **herkes (lider dahil) PR + CI required-check** — bypass yok.
- Sürüm sabitleme YOK (bilinçli trade-off — canlılık ilkesi pinning'le çelişir).
  Yumuşatma (D6): GATE-geçen commit'lerde hareketli **`stable` tag** → core kırılırsa
  `git checkout stable` = deterministik bilinen-iyiye dönüş (prosedür: MAINTENANCE §4).
- Ekip senkronu: makine başına tek `git pull` (DEV_CORE clone'unda); projelerde pull
  yoktur. `session_start` "origin'in gerisinde" uyarısı verir (throttle'lı).

### 5. K8 — YAN-KURULUM modeli (in-place dönüşüm DEĞİL)

Mevcut projelerin bu mimariye geçişi **yerinde dönüşüm olarak YAPILMAZ**. Karar (K8):

- Yeni dünya **yeni kök altında sıfırdan** kurulur (`C:\IX\`): DEV_CORE clone + proje
  clone'u (tam git geçmişi yeni org reposuna push'lanır) + junction'lar + ince CLAUDE.md.
- Eski dünya (`<LEGACY_ROOT>` lokal kökü + eski GitHub repoları) **DONDURULMUŞ
  SALT-OKUNUR YEDEK** olur: okuma serbest (legacy referanslar), yazma `pre_tool_guard`
  **freeze-guard**'ıyla BLOK'lu (`project.yaml frozen_readonly_paths`; risk R10 —
  kas-hafızasıyla eski klasöre yazma).

**Gerekçe:** (a) **Rollback radikal basitleşir** — en kötü senaryoda eski klasörden
çalışmaya devam edilir, git-revert akrobasisi gerekmez; yeni kök istenirse komple
silinebilir. (b) Yarı-dönüşmüş ara-durum riski sıfırlanır (in-place'te her adım geri
alınabilir olmak zorundaydı). (c) Eski repo/klasör "son fotoğraf" commit'iyle tarihsel
kanıt olarak donar. İlk uygulayan projede model kanıtlandı (GATE A–D kapanışları:
yan-kurulum + freeze-guard + sızıntı-gate'leri canlı doğrulandı).

## Reddedilen alternatifler

| Alternatif | Neden reddedildi |
|---|---|
| **Template-repo + kopya (önceki model)** | Yaşanmış sorun: kopya-drift + batch-port senkron yükü + proje sayısıyla çarpan maliyet. Bu ADR'nin varlık sebebi; `T12`/`template_drift` emekli edildi, yerine SORU 0 (yazım-anı tek-hedef) geldi. |
| **git submodule** | Pinned-SHA modeli "anında yansıma" ilkesini kırar: core'daki her düzeltme için proje başına bump-commit gerekir — senkron yükü başka biçimde geri gelir. Ayrıca submodule ergonomisi (detached HEAD, unutulan `--recurse`) günlük sürtünmedir. Not: bir proje bilinçli DONDURULACAKSA nokta-çözüm olarak submodule'a dönülebilir (kayıtlı istisna). |
| **git subtree** | İçerik proje repolarına FİZİKSEL kopyalanır → drift geri gelir + metodoloji (fikri sermaye) her müşteri-proje reposuna sızar (R1'in ta kendisi). Merge-back akışı da çift-yönlü senkron yüküdür. |
| **Kullanıcı-seviyesi `~/.claude` paylaşımı** | Git'te değil → ekibe/makineler-arasına akmaz, PR/CI disiplinine bağlanamaz; kapsam taşması (makinedeki SAP-dışı projelere de yüklenir); core'la çift-kaynak drift'i. Kural: user-level dosyaya metodoloji YAZILMAZ (CLAUDE.core.md §5). |
| **Tek monorepo (core + tüm projeler)** | Proje repoları ayrı müşteri/erişim sınırlarıdır: monorepo'da erişim izolasyonu ve "metodoloji ekip-içi, proje içeriği proje-ekibiyle" ayrımı kaybolur; git geçmişleri karışır; bir projeyi dondurma/devretme granülerliği yok olur. |
| **Claude Code plugin dağıtımı** | Yapısal olarak cazip ama bugün canlılık ilkesiyle çelişir — detay ve off-ramp aşağıda (D28). |

## Plugin off-ramp (D28) — bilinçli açık kapı

Claude Code plugin mimarisi skills/agents/hooks/commands/MCP'yi **tek versiyonlu birim**
olarak paketler ve bu mimarinin üç risk sınıfını (R4 worktree-junction kırığı, R9
özyinelemeli-silme, R1 sızıntı) yapısal olarak yok ederdi. Buna rağmen REDDedildi:

1. Plugin kurulumu **cache-KOPYASI**dır ve sürüm/update akışıyla gelir → 1 numaralı
   ilkemiz olan "aynı makinede ANINDA yansıma" canlılığını bozar (düzelt → paketle →
   sürümle → güncelle döngüsü, junction'ın sıfır-adımına karşı).
2. `core/scripts`, `standards/`, `playbook/` path-mimarisi (hook path'leri, validator
   keşfi, `path=core/` arama konvansiyonu) plugin yerleşimine büyük refactor ister.

**Off-ramp koşulu:** plugin mimarisi olgunlaşır da canlı/linkli geliştirme modunu
(kopyasız, working-tree'den yükleme) desteklerse geçiş yeniden değerlendirilir.
**Mevcut yapı buna hazır tutulur:** (a) plugin-şekilli varlıklar zaten tek çatı altında
gruplu (`claude/` → agents · skills · commands · memory-seed · template'ler); (b) içerik
genericize + `applies_to` etiketli — paketlenebilir durumda; (c) hook giriş noktası tek
(shim) ve settings template'ten üretiliyor — path değişimi tek noktadan; (d) mekanizma/
değer ayrımı (`project.yaml`) sayesinde core içeriği proje-bağımsız. Yani geçiş bir
**paketleme işi** olur, içerik yeniden-yazımı değil.

## Sonuçlar / Trade-off'lar

- **Windows-bağımlılık:** junction NTFS/Windows mekanizmasıdır. Ekip Windows'ta çalıştığı
  sürece maliyetsiz (`mklink /J` admin istemez, cross-volume çalışır); platform değişirse
  symlink karşılığı gerekir. Yedekleme/sync araçları (OneDrive vb.) yeni kökü KAPSAMAZ (R5).
- **`resolve()` tuzağı (D24):** junction üzerinden koşan core script'inde
  `Path(__file__).resolve()` CORE reposuna çözülür → proje-artefaktı (`.conn_adt`,
  `<source_root>/`…) yanlış kökte aranır. Kural: proje kökü İÇİN TEK kaynak
  `utils/project_config.project_root()` (env `CLAUDE_PROJECT_DIR` → cwd); `__file__`
  yalnız core-içi varlıklar için meşru. Yaşanmış vaka + denetim komutu:
  [playbook/lessons-learned.md](../../playbook/lessons-learned.md) **PATTERN #10**.
- **Arama-görünürlük (D29):** Grep aracı `.gitignore`'a uyar → proje kökünden yapılan
  aramalar ignore'lu `core/`'u SESSİZCE atlar ("sonuç yok" ≠ "core'da yok"). Kural:
  metodoloji araması DAİMA `path=core/` ile ([CLAUDE.core.md](../../CLAUDE.core.md)
  🔎 ARAMA TALİMATI); Glob asimetriktir (ignore'a uymaz) — asimetriye güvenilmez.
- **Tek-kopya kırık riski (R2/R9):** core'daki kırık TÜM projelere anında yayılır →
  önlem CI required-check + `stable` tag rollback; junction hedefine özyinelemeli silme
  (`git clean`/`rm -rf`/`Remove-Item -Recurse`…) `pre_tool_guard`'da BLOK (güncel
  toolchain'de komutların junction içine inmediği deneysel kanıtlı, guard toolchain-
  çeşitliliği sigortasıdır).
- **Worktree'ler:** junction'lar ve gitignore'lu runtime dosyaları (`.conn_adt` vb.)
  worktree'de kendiliğinden YOKTUR → `team_setup --provision-worktree` kurar; junction'sız
  worktree'de oturum açılmaz (R4 önlemi).
- **Davranış güvenlik duvarı (§11) ilişkisi:** bu mimari firewall'un ön-koşuludur —
  *davranış taşıyan dosya ya core'dan junction'la gelir (tek kaynak, PR+CI'lı) ya
  behavior-manifest'te kayıtlıdır* ilkesi ancak davranışın tek fiziksel evi varken
  kurulabilir. Davranış-yüzeyi path'leri (CLAUDE.md, `.claude/**`, `.mcp.json`,
  `project.yaml`, hook_shim) projelerde yalnız lider-onaylı PR ile değişir (F1);
  session_start manifest-diff'i sapmayı yakalar (F2). Özet: [CLAUDE.core.md](../../CLAUDE.core.md) §8.
- **Yasaklar istisnası (ADR 0021):** "kopya yok" ilkesi tek yerde bilinçli delinir —
  KESİN YASAKLAR her projenin kök CLAUDE.md'sine fiziksel damgalanır (junction kırılsa
  da anayasa yüklü); drift tek-kanonik + `check_kesin_yasaklar` guard'ıyla önlenir.
- **Numaralandırma sonucu:** core ADR'leri bu repoda `NNNN` serisiyle devam eder;
  proje-ADR'leri proje reposunda `<PROJE>-NNN` serisindedir (çakışma önleme).
