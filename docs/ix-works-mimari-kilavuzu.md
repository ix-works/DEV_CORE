# ix-works Mimarisi — Kurulum ve İşletim Kılavuzu

> **Amaç.** Bu belge, birden çok SAP geliştirme projesini tek bir metodoloji çekirdeği
> üzerinden yürüten "ix-works" mimarisini tanımlar. Hedef okuyucu iki gruptur: mimariyi
> değerlendiren/işleten **yöneticiler** (Bölüm 0–1 ve 15 yeterlidir) ve sistemi kuran/kullanan
> **geliştiriciler** (tüm belge). Belge, sistemin fiili durumunu yansıtır; her yetenek,
> arkasındaki dosya/kural referansıyla birlikte anlatılır.
>
> **Sürüm.** 2026-07-10. Sayılar (hook/validator/tool adedi) o tarihte canlı ağaçtan ölçülmüştür.
> Belgedeki tüm proje/paket adları örnektir (`<PROJE>`, `<ORG>`, `ZSD001_CLC`); gerçek bir
> kurulumda kendi değerlerinizle değişir. Standart SAP nesneleri (VBAK, LIKP, BAPI_*) gerçektir.
>
> **Bu sürümdeki büyük değişiklikler.** (a) Talimat-katmanı yeniden bölündü: `AGENTS.md`'nin
> hiçbir oturumda yüklenmediği ölçüldü → L1a/L1b/L1c ayrımı ve glob-tetiklemeli `claude/rules/`.
> (b) `pre_tool_guard` 12 katmandan **8 kurala** indirildi (merdiven ilkesi). (c) MCP tool yüzeyi
> profil-bazlı oldu (fail-closed). (d) Üç yeni gate: C-MEM-01, C-REG-01, C-TPL-01.

---

## İçindekiler

- [0. Yönetici Özeti](#0-yönetici-özeti)
- [1. Mimari Felsefe: Canlı Çekirdek + Junction](#1-mimari-felsefe-canlı-çekirdek--junction)
- [2. Temel Yetenekler ve Tasarım Kararları](#2-temel-yetenekler-ve-tasarım-kararları)
- [3. DEV_CORE Anatomisi](#3-dev_core-anatomisi)
- [4. Proje Klasörü Anatomisi](#4-proje-klasörü-anatomisi)
- [5. Çoklu-Proje Flow & Junction Mimarisi](#5-çoklu-proje-flow--junction-mimarisi)
- [6. Enforcement Katmanı — Ne, Ne Zaman Tetiklenir](#6-enforcement-katmanı--ne-ne-zaman-tetiklenir)
- [7. Kalite Kapıları: Validator + Reviewer + Coverage](#7-kalite-kapıları-validator--reviewer--coverage)
- [8. Kural Mimarisi (L1–L4) ve SORU 0](#8-kural-mimarisi-l1l4-ve-soru-0)
- [9. İş-Alım: Intake Triage Gate (ITG)](#9-iş-alım-intake-triage-gate-itg)
- [10. SAP ADT MCP Sunucusu](#10-sap-adt-mcp-sunucusu)
- [11. Kurumsal Hafıza (Memory) Sistemi](#11-kurumsal-hafıza-memory-sistemi)
- [12. Çok-Ajanlı Çalışma Modeli](#12-çok-ajanlı-çalışma-modeli)
- [13. GitHub Mimarisi ve Çalışma Akışı](#13-github-mimarisi-ve-çalışma-akışı)
- [14. Sağlık ve Kalite Araçları](#14-sağlık-ve-kalite-araçları)
- [15. Güvenlik, Gizlilik ve Uyumluluk](#15-güvenlik-gizlilik-ve-uyumluluk)
- [16. Onboarding: Yeni Geliştirici ve Yeni Proje](#16-onboarding-yeni-geliştirici-ve-yeni-proje)
- [17. Bilinen Sınırlar ve Açık Kalemler](#17-bilinen-sınırlar-ve-açık-kalemler)
- [EK-A. Karar Kayıtları (ADR) Dizini](#ek-a-karar-kayıtları-adr-dizini)
- [EK-B. Terminoloji](#ek-b-terminoloji)

---

## 0. Yönetici Özeti

ix-works, tek bir merkezi "metodoloji çekirdeği" (DEV_CORE) ile ona bağlı proje repoları
arasında **işletim sistemi düzeyinde bağlantı (junction)** kuran bir çalışma modelidir.
Metodoloji — kodlama standartları, kalite kapıları, yapay-zekâ ajan davranış kuralları,
SAP bağlantı araçları, kurumsal hafıza — bir kez merkezde tanımlanır; tüm projeler bunu
otomatik devralır. Bir standart veya ders bir kez yazıldığında, bağlı tüm projelerde aynı
anda geçerli olur; kopyalama ve sürüm-kayması (drift) oluşmaz.

Modelin üç temel özelliği:

1. **Kural ile uygulama ayrılmaz.** Her kalite kuralı, atlanamayan bir teknik kapıyla
   (validator, hook, gate) zorlanır. Kural "belgede yazılı" değil, "araç tarafından
   uygulanan" bir şeydir. İnsan disiplinine değil, mimariye dayanır.

2. **Yapay-zekâ ajanı da kurallara tabidir.** Ajanın her önemli eylemi (dosya yazma, SAP'ye
   erişim, komut çalıştırma) gerçek zamanlı denetlenir. Standart SAP nesnesine dokunma,
   donmuş yedeğe yazma veya fikri-sermaye sızdırma gibi eylemler **eylem anında** reddedilir.

3. **Değişiklikler denetlenebilir ve geri alınabilir.** Her değişiklik kısa-ömürlü dal +
   inceleme (PR) + otomatik kontrol (CI) sürecinden geçer. Merkezi çekirdek, bilinen-iyi
   bir noktaya (`stable` etiketi) tek adımda döndürülebilir.

Model gerçek kurumsal SAP ortamları için tasarlanmıştır: Windows üzerinde çalışır, şirket-içi
(on-prem) SAP sistemlerine VPN üzerinden bağlanır, birden çok sistem katmanını (DEV/QA/PRD)
ayrı yönetir ve KVKK/veri-gizliliği kısıtlarını gözetir.

> **Yönetici için tek cümlelik özet:** Kalite, kişilerin dikkatine değil, atlanamayan
> otomatik kapılara bağlanmıştır; yapay-zekâ dahil hiçbir aktör bu kapıları geçemez.

---

## 1. Mimari Felsefe: Canlı Çekirdek + Junction

### 1.1 Çözülen sorun
Birden çok proje aynı metodolojiyi (standartlar, hook'lar, validator'lar, şablonlar)
kullandığında, klasik yaklaşım her projeye bir kopya koymaktır. Kopyalar zamanla birbirinden
uzaklaşır (drift); bir düzeltme bir projede yapılır, diğerlerine taşınmaz; hangi kopyanın
güncel olduğu belirsizleşir. Proje sayısı arttıkça bakım yükü katlanır.

### 1.2 Çözüm — tek canlı kaynak
Metodolojinin tamamı `DEV_CORE` adında **tek bir repoda** tutulur ve her projeye Windows
**junction** (dizin bağlantısı) ile bağlanır. Proje klasöründeki `core/` girişi, fiziksel
olarak DEV_CORE'un çalışan kopyasını gösterir:

- Metodoloji **bir yerde** yaşar; tüm projeler onu **anlık** görür.
- Bir kural/ders bir kez yazılır, junction'la her projeye ulaşır.
- Kopya-drift **yapısal olarak imkânsızdır** — kopya yoktur.

Karar kaydı: **ADR 0020** (Canlı-Çekirdek Junction Mimarisi).

### 1.3 Neden junction (ve neden diğerleri değil)
| Alternatif | Neden seçilmedi |
|---|---|
| Her projeye kopya | Drift + N-kat bakım (çözülen sorunun kendisi) |
| Git submodule | Sürüm-sabitleme "canlı"lığı bozar; her projede ayrı pin/pull yükü |
| Git subtree | Geçmiş şişer; senkron karmaşık |
| Kullanıcı-seviyesi paylaşım (`~/.claude`) | Git-dışı (ekibe akmaz); kapsam taşması |
| Tek monorepo | Projeler ayrı yaşam-döngüsü/izin/repo ister |

Junction, "canlı tek kaynak" ile "projelerin bağımsız git repoları" gereksinimlerini aynı
anda karşılayan tek seçenektir. DEV_CORE ile projeler arasında **git bağı yoktur**; yalnız
dosya-sistemi düzeyinde bağlıdırlar.

### 1.4 Junction'ın bedeli — arama körlüğü (D29)
Junction ücretsiz değildir. `Grep`/`Glob` araçları junction'ı **takip etmez** ve
**sessizce boş** döner — "dosya yok" ile ayırt edilemez. Kontrollü deneyle ölçülmüştür:
sebep `.gitignore` değildir; junction'ın kendisidir.

Yapısal çözüm: `governance/CORE-INDEX.md` — proje reposunda **gerçek** bir dosya olarak durur,
kökten aranıp bulunur ve doğru `core/...` yolunu verir. `build_core_index.py` üretir,
`check_core_index_fresh.py` (C-IDX-01) tazeliğini zorlar. Doğrudan arama gerekiyorsa daima
`path=core/` verilir.

**Kural:** kökten sıfır-sonuç, "core'da yok" anlamına **gelmez**.

### 1.5 Metodoloji vs proje ayrımı (SORU 0)
Yeni bilgi üretildiğinde tek soru sorulur: *"Bu metodoloji mi, projeye mi özel?"*
Metodoloji-nitelikli her şey `DEV_CORE`'a; projeye-özel her şey proje reposuna gider.
Bu ayrım çekirdeğin jenerik kalmasını, proje reposunun iş-bilgisini taşımasını sağlar.
(Karar ağacı: Bölüm 8.)

---

## 2. Temel Yetenekler ve Tasarım Kararları

**1. Kendi kendini denetleyen kalite altyapısı.**
`ix_doctor` (7 katman) kurulumun bütünlüğünü doğrular. Guard katmanları dönemsel olarak
**bozuk girdiyle** sınanır; bu, bir kuralın "tanımlı olması" ile "fiilen çalışması"nı ayrı
ayrı doğrular. (Bölüm 14)

**2. Yapay-zekâ ajanı için davranış denetimi.**
Ajanın her eylemi `pre_tool_guard`'dan geçer. Temel yasaklar, projenin kök yapılandırma
dosyasına **fiziksel olarak damgalanmıştır**; junction kopsa bile yüklüdürler. (Bölüm 6)

**3. Her kural bir kapıyla zorlanır.**
*"Gate'siz kural, kuralsızdır"* (ADR 0019). `check_rule_gate_coverage` bu bağı hesaplattırır;
elle-bakımlı eşleme tutulmaz. (Bölüm 7)

**4. Talimatın yüklendiği KANITLANIR, varsayılmaz.**
2026-07-10 denetiminde `AGENTS.md`'nin (356 satır, 25 zorunlu kural) **hiçbir oturumda
context'e girmediği** ölçüldü: harness `CLAUDE.md` okur, `AGENTS.md` okumaz ve bağlantı bir
`@import` değil düz markdown link'ti. Üstelik oturum-başı ekran teyidi her seferinde
"AGENTS.md yüklendi" diyordu. Sonuç: talimat katmanı L1a/L1b/L1c olarak ayrıldı ve
`InstructionsLoaded` hook'u yüklemeyi **loglar**. (Bölüm 8)

> **İlke:** Markdown link hiçbir şey yüklemez. "Yüklendi" bir iddia değil, bir ölçümdür.

**5. Biriken kurumsal hafıza — sınırları bilinerek.**
Oturum-başı yüklenen hafıza indeksinin sert bir tavanı vardır (ilk 200 satır **veya** ilk
25 KB; hangisi önce gelirse). Aşıldığında sessizce kesilir. `check_memory_index.py` (C-MEM-01)
bu bütçeyi ve indeks bütünlüğünü ölçer. (Bölüm 11)

**6. Kanıta dayalı çalışma ("tahmin yasak").**
Hatırlanan bilgi **hipotez**, canlı sistem **otoritedir** (ADR 0016). Bir araç "başarılı"
dediğinde bu kanıt sayılmaz; readback yapılır. (Bölüm 6, 10)

**7. İşe-orantılı alım süreci (ITG).**
Talep geldiğinde kapsam sınıflanır (S0/S1/S2), modül kural-paketi yüklenir, isterlerden
araştırılacak konular çıkarılır, üç eksende araştırma yapılır. Küçük işe ağır süreç binmez;
kapsamlı işte disiplin atlanmaz. (Bölüm 9)

**8. Profil-farkında araç yüzeyi (fail-closed).**
MCP tool'ları `available_on` etiketi taşır; projenin SAP profiline uymayan tool `tools/list`'te
**görünmez**. `sap_profile` eksik/geçersizse yüzey kesilir, yalnız `ping` açılır. Prompt'a
"bunu kullanma" demek ricadır; tool'u gizlemek sınırdır. (Bölüm 10)

**9. Çok-katmanlı SAP hedefi.**
Aynı çekirdek dört profili destekler: `ecc`, `s4_private`, `s4_public`, `btp_abap`.

**10. Gerçek kurumsal ortam desteği.**
Windows junction, VPN-kopukluğunu izleyen arka-plan bekçisi (watchdog), çoklu sistem-katmanı
ve Windows'a özgü kodlama tuzaklarının çözümü — laboratuvar değil, saha kullanımı için.

---

Aşağıdaki üç bölüm (3–5) iki fiziksel katmanın anatomisini ve onları bağlayan junction
mekanizmasını tanımlar.

## 3. DEV_CORE Anatomisi

DEV_CORE, metodolojinin tek fiziksel kopyasının tutulduğu **public** git reposudur. Public
olması genericize disiplinini zorunlu kılar (Bölüm 15.2).

### Kök seviyesi dosyalar

| Dosya | İçerik / işlev |
|---|---|
| `CLAUDE.core.md` | Çekirdek loader. Proje `CLAUDE.md`'si `@core/CLAUDE.core.md` ile yükler. Katman özeti (L1a–L4), **§1.1 her-oturum davranış değişmezleri**, SAP profil modeli, oturum protokolü, T1–T11 + SORU 0, gate tablosu, dosya indeksi. |
| `AGENTS.md` | **L1c — derin davranış referansı. OTOMATİK YÜKLENMEZ**; açıkça okunmalıdır. Git workflow detayı, ADT işlem sırası, obje→klasör eşlemesi, reviewer pre-flight ayrıntısı. |
| `MAINTENANCE.md` | Canlı-çekirdek işletim el kitabı: PR/CI akışı, `stable` tag ile rollback, `project.yaml` anahtar kataloğu. |
| `ONBOARDING.md` | Yeni/güncellenen geliştiriciyi ortamla senkron etme adımları. |
| `PROJECT_BOOTSTRAP.md` | Yeni proje açılış prosedürü (STEP 0–6 + kabul kapısı). |
| `.github/workflows/core-ci.yml` | Çekirdeğin kendi CI'ı (`gates` job). |

### Dizinler

```text
DEV_CORE/
├── claude/          Claude Code varlıkları (agent, skill, rules, command, template, memory-seed)
├── scripts/         Python araçları — hooks/ + validators/ + git-hooks/ + tests/ + utils/
├── mcp_servers/     SAP ADT MCP server (typed tool katmanı + guardrail'ler)
├── standards/       L2 — stabil kurumsal standartlar (10 dosya)
├── playbook/        L3 — ADT pattern bankası + checklists/ + modules/ + templates/ (41 md)
├── profiles/        SAP profil yetenek matrisleri (4 yaml)
├── governance/      ADR'ler (21) + işletim modeli + tooling envanteri
├── templates/       Yeni-paket iskelet şablonları
├── docs/            Bu kılavuz + yönetici sunumu
└── intake/          Dış içerik karantina/gümrük alanı
```

#### `claude/` — Claude Code varlıkları

Proje `.claude/` altındaki **beş junction** (agents, skills, commands, rules) ve `core/`
buraya bakar.

| Yol | İçerik |
|---|---|
| `agents/` | **6 rol tanımı.** Tek-yazıcı (single-writer) modeli — aşağıda tablo. Her rolün başında "sen auto-memory GÖRMEZSİN + kanıt kuralları" bloğu vardır (Bölüm 11.5). |
| `skills/` | **3 project skill:** `sap-abap-dev` (SAP/ABAP/RAP/CDS/DDIC yönlendirme), `intake-triage` (iş-alım protokolü, native semantik keşif), `playwright-cli` (tarayıcı otomasyonu). |
| `rules/` | **L1b — glob-tetiklemeli davranış kuralları.** Eşleşen dosya okunduğunda otomatik yüklenir; startup maliyeti sıfırdır. Bugün 3 dosya (`sap-source-protokolu`, `ui5-freestyle`, `README`). |
| `commands/` | Slash-komutlar (`onboard`). |
| `memory-seed/` | Yeni proje memory tohumu: `MEMORY.md` indeksi + 85 `feedback_*.md` ders dosyası. |
| `CLAUDE.project.template.md` | Yeni proje ince `CLAUDE.md` şablonu. |
| `README.project.template.md` | Yeni proje kök `README.md` şablonu. |
| `settings.template.json` | Proje `.claude/settings.json` şablonu — hook zinciri. Gate: **C-TPL-01**. |
| `hook_shim.template.py` | Proje-lokal hook yönlendiricisi şablonu (D15). |
| `git-hooks/pre-commit.template` | Proje pre-commit gate şablonu (statik katman ③). |
| `workflows/guard.template.yml` | Proje CI şablonu (3 job). |
| `kesin-yasaklar.canonical.md` | KESİN YASAKLAR kanonik metni; her projenin kök `CLAUDE.md`'sine fiziksel damgalanır (ADR 0021). |
| `conn_adt.template` / `managed-policy.template.json` / `CODEOWNERS.template` | Bağlantı / izin / sahiplik şablonları. |

**Agent rolleri (6):**

| Rol | Yetki sınırı |
|---|---|
| `adt-gateway` | SAP'ye yazabilen **tek** rol. Tüm create/push/activate/delete/DDIC/post_shell buradan geçer. |
| `backend-expert` | ABAP/RAP/CDS/DDIC/class. Tasarım + yerel kaynak + read-only analiz. **SAP-yazma tool'u yok.** |
| `frontend-expert` | Freestyle UI5 + OData V2. Yerel UI kaynağı + read-only. **SAP-yazma tool'u yok.** |
| `bug-expert` | Adversarial inceleme (read-only). Verdict PASS/WARNING/BLOCKER. Yazmaz. Her review taze. |
| `sap-feature` | Modül/uygulama sahibi — uçtan uca tasarım + yerel kaynak, read-only. |
| `sap-research` | Salt-okunur keşif/analiz + web araştırması. Yalnız `.tmp/` rapor yazar. |

#### `scripts/` — Python araçları (89 tekil + alt dizinler)

**`scripts/hooks/` — 15 olay-tetikli hook** (hepsi `hook_shim.py` üzerinden):

`session_start` · `tooling_radar_check` · `instructions_loaded_log` · `skill_injector` ·
`intake_triage` · `pre_tool_guard` · `pull_before_edit` · `sap_worktype_hint` ·
`itg_backstop` · `watchdog_launch` · `post_validate` · `post_tool_failure` ·
`config_change_guard` · `pre_compact` · `watchdog_stop`

> Envanterin şablonla eşliği **C-TPL-01** gate'iyle zorlanır: `scripts/hooks/` altına düşen
> her hook `settings.template.json`'da kablolu olmalıdır. Aksi hâlde yeni açılan proje
> eksik korumayla açılır — 2026-07-10'da tam olarak bu oldu (3 hook şablonda yoktu).

**`scripts/validators/` — 43 `check_*.py`; 22'si `run_all_validators`'a kayıtlı.**
Tek komut `run_all_validators.py` core + proje `validators-local/` ile birlikte, profil-modlu
koşar. `run_review.py` SAP yazma öncesi reviewer pre-flight'ıdır (ADR 0006).

**`scripts/git-hooks/` + `scripts/tests/`:** çekirdeğin kendi pre-commit gate'i
(`core_precommit.py`: genericize-leak + link-audit + applies_to şeması) ve guard konformans
testleri (`guard_conformance.py`, `test_pre_tool_guard.py`).

**Tekil araçlar (seçme):**

| Araç | İşlev |
|---|---|
| `init_project.py` | Yeni proje iskeletini template'lerden **üretir** (kopyalamaz). |
| `team_setup.py` | Junction kur/onar, pre-commit kablola, plugin + memory seed, CORE-INDEX üret. |
| `bootstrap_package.py` | Yeni SAP paketi iskeleti (`.rules.md` + docs + SESSION_NOTES). |
| `genericize_common.py` | Sızıntı desenlerinin **tek kaynağı** (pre-commit + pre_tool_guard aynı modülü kullanır). |
| `sync_yasaklar.py` | KESİN YASAKLAR kanonik → tüm projeleri yeniden damgalama. |
| `ix_doctor.py` / `sap_doctor.py` | Ortam / SAP bağlantı sağlık teşhisi. |
| `deploy_ui.py` | Freestyle UI kanonik non-interaktif deploy (build + deploy + canlı-hash). |
| `behavior_manifest.py` | Davranış-yüzeyi manifest üretimi/diff. |
| `seed_memory.py` | Memory tohumlama; `.seed-manifest.json` ile rename/silme uzlaştırma. |
| `build_core_index.py` | `governance/CORE-INDEX.md` üretimi (junction arama körlüğü çözümü). |
| `build_package_index.py` | `governance/package-registry.md` üretimi + `--check` tazelik. |
| `switch_tier.py` | Çoklu-tier SAP bağlantı değişimi (ADR 0010). |
| `sap_sync_pull.py` / `source_drift.py` | Canlı-repo senkron / drift tespiti (ADR 0016). |
| `utils/project_config.py` | Proje kökü + `project.yaml` okuma tek kaynağı (D24). |

#### `mcp_servers/sap_adt/` — SAP ADT MCP server

`stdio` transport'lu typed tool katmanı (ADR 0007). Bileşenler: `server.py`, `_app.py`
(`profil_tool` dekoratörü), `_profile.py` (D34d profil kapısı), `guardrails.py`,
`data_guard.py`, `_reviewer.py`, `_conn.py`, `tools/`, `tests/`. (Ayrıntı: Bölüm 10.)

#### `standards/` (L2) · `playbook/` (L3) · `profiles/` · `governance/`

- **`standards/`** — 10 dosya, `applies_to:` frontmatter'lı, düşük değişim sıklığı:
  naming, klasik backend, Fiori UI5, FS/TS dokümantasyon, RAP, klasik dialog, çıktı/formlar,
  klasik F1 yardımı, ambalajlama talimatı + indeks.
- **`playbook/`** — 41 md: obje-tipi bazlı ADT pattern bankası (`adt-*`), `lessons-learned`,
  `howto-*`, `intake-triage.md`; alt dizinler `checklists/` (16), `templates/`, `modules/`.
- **`profiles/`** — `ecc` · `s4_private` · `s4_public` · `btp_abap`. **Matris rehberdir,
  kanıt değildir:** capability iddiası canlı testle doğrulanır.
- **`governance/`** — `decisions/` (21 ADR), `agent-teams-operating-model.md`,
  `tooling-plugins.md`, `tooling-radar.md`.

#### `intake/` — dış içerik gümrüğü

Dışarıdan gelen her metodoloji parçası core'un canlı yüzeyine doğrudan girmez; önce buraya
iner, güvenlik + lisans + genericize incelemesinden geçer, sonra PR ile hedefe taşınır.
Sebep: core canlıdır — buraya giren şey junction'lı tüm projelerde **anında** etkilidir.

---

## 4. Proje Klasörü Anatomisi

```text
<PROJE>/
├── core/  ═══════════════════► DEV_CORE                    (junction)
├── .claude/
│   ├── agents/  ═════════════► DEV_CORE/claude/agents      (junction)
│   ├── skills/  ═════════════► DEV_CORE/claude/skills      (junction)
│   ├── commands/ ════════════► DEV_CORE/claude/commands    (junction)
│   ├── rules/   ═════════════► DEV_CORE/claude/rules       (junction — L1b)
│   ├── settings.json            (proje-lokal, commit'li — hook zinciri)
│   ├── settings.local.json      (kişisel, gitignore)
│   ├── behavior-manifest.json   (davranış-yüzeyi manifest, gitignore runtime)
│   └── .current_session / .mcp_active_system / .itg_shown.json …  (runtime state, gitignore)
├── CLAUDE.md                    (ince loader — yasaklar damgalı + @core import + proje-özel)
├── README.md                    (init_project üretir)
├── project.yaml                 (proje kimliği: profil, source_root, gate config'leri)
├── .conn_adt                    (SAP bağlantı — gitignore)
├── conn/                        (çoklu-tier .env'ler — *.env gitignore)
├── .mcp.json                    (MCP server tanımı — core'dan yüklenir, env-first)
├── .gitignore / .gitattributes  (SIZINTI KİLİDİ + sırlar + runtime + CRLF politikası)
├── .github/workflows/guard.yml  (CI: core-leak · validators · behavior-surface)
├── .github/CODEOWNERS
├── scripts/
│   ├── hook_shim.py             (proje-lokal hook yönlendiricisi — commit'li)
│   ├── git-hooks/pre-commit     (statik gate ③ — team_setup kablolar)
│   └── validators-local/        (proje-özel validator'lar)
├── <source_root>/               (SAP kaynak kodu — modül-bazlı; ad project.yaml'dan)
│   └── <MODULE>/<PKG>/           (ör. SD/ZSD001_CLC/ — cds classes docs ui .rules.md)
├── governance/                  (proje ADR'leri, deferred-triggers, package-registry, CORE-INDEX)
├── playbook-local/ standards-local/   (proje-özel overlay — core otokeşif)
└── .tmp/                        (scratch/çıktı — gitignore)
```

### Core'dan gelen vs proje-özel — net ayrım

| Dosya / dizin | Kaynak | Not |
|---|---|---|
| `core/`, `.claude/{agents,skills,commands,rules}/` | **Junction → DEV_CORE** | Tüm metodoloji. Proje reposuna commit'lenmez (gitignore + pre-commit + CI). |
| `CLAUDE.md`, `README.md`, `.claude/settings.json`, `scripts/hook_shim.py`, `scripts/git-hooks/pre-commit`, `.mcp.json`, `project.yaml` | **Proje-lokal (commit'li)** | Template'ten **üretilir**. Metodoloji yazılmaz (SORU 0). |
| `.conn_adt`, `conn/*.env`, `.claude/project.local.yaml`, `.csrf_token.json` | **Proje-lokal (gitignore)** | Sırlar. Yalnız `*.template` commit'li. |
| `behavior-manifest.json`, `.current_session`, `.itg_shown.json` … | **Proje-lokal (gitignore)** | Runtime state, paylaşılmaz. |
| `<source_root>/<MODULE>/<PKG>/` | **Proje-özel (commit'li)** | SAP kaynağı, docs, `.rules.md` (L4), SESSION_NOTES. |
| `governance/` | **Proje-özel (commit'li)** | Proje ADR'leri, deferred-triggers, package-registry, CORE-INDEX, `*-RESUME.md`. |
| `playbook-local/`, `standards-local/`, `validators-local/` | **Proje-özel (commit'li)** | Overlay: core mekanizmaları otomatik keşfeder. |

**Ayrımın özü:** davranış taşıyan her şey ya core'dan junction'la gelir (tek kaynak, PR+CI'lı)
ya da davranış-manifest'te kayıtlıdır.

---

## 5. Çoklu-Proje Flow & Junction Mimarisi

### 5.1 Junction nasıl kurulur ve çalışır

Junction, Windows NTFS'in dizin bağlama mekanizmasıdır (`mklink /J`). Admin/dev-mode
gerektirmez, cross-volume çalışır. Proje klasöründeki **beş** yol DEV_CORE'a bağlanır:

```text
<PROJE>\core             ──► DEV_CORE
<PROJE>\.claude\agents   ──► DEV_CORE\claude\agents
<PROJE>\.claude\skills   ──► DEV_CORE\claude\skills
<PROJE>\.claude\commands ──► DEV_CORE\claude\commands
<PROJE>\.claude\rules    ──► DEV_CORE\claude\rules
```

Kurulumu `team_setup.py` yapar: Python ≥3.10 + MCP requirements, core reposunda ve **projede**
`core.hooksPath scripts/git-hooks`, beş junction kur/doğrula (tek tek rapor), eksik proje-lokal
dosyaları template'ten tamamla, plugin + memory seed, `CORE-INDEX` üret, smoke test. Junction
kopmuşsa `--repair-junctions` yalnız onarımı koşar.

> ⚠ **Junction silme tuzağı.** `rm -rf <proje>` bir junction'a girerse **hedefi** (DEV_CORE)
> siler. Proje klasörü boşaltılacaksa junction'lar önce *bağlantı olarak* kaldırılır
> (`rmdir` — `/s` YOK), sonra içerik silinir.

Junction canlı bir bağdır; DEV_CORE working tree'sindeki her değişiklik tüm projelerde anında
görünür. Sürüm sabitleme yoktur — canlılık ilkesi pinning'le çelişir. Rollback ihtiyacı
`stable` tag ile karşılanır.

### 5.2 Çağrı zinciri: proje → DEV_CORE

```text
.claude/settings.json
   └─ hook komutu: python ${CLAUDE_PROJECT_DIR}/scripts/hook_shim.py <hook_adi>
        └─ hook_shim.py (proje repo'da commit'li, ~10 satır)
             ├─ core/ junction sağlam mı?  ── HAYIR ─► NET hata + onarım komutu bas, dur
             └─ EVET ─► core/scripts/hooks/<hook_adi>.py  (runpy — aynı süreç, +0 ms)
```

Shim bilinçli bir mini kopya-artefaktıdır: `settings.json` doğrudan `core/`'a işaret etseydi,
junction koptuğunda kontrolü yapacak kod da kopuk junction'ın arkasında kalırdı. Shim'in core
kanoniğiyle drift'i `session_start` hook'unda SHA-256 ile denetlenir.

**Junction `resolve()` tuzağı (D24):** junction üzerinden koşan core script'inde
`Path(__file__).resolve()` fiziksel CORE reposuna çözülür → proje-artefaktı yanlış kökte aranır.
Kural: proje kökü için tek kaynak `utils/project_config.project_root()`; `__file__` yalnız
core-içi varlıklar için meşru. Gate: `check_project_root_resolution` (CORE-01).

### 5.3 project.yaml profil sistemi — hangi kural aktif

Mekanizma core'da, **değer projededir**. Core hiçbir değeri hard-code etmez.

```text
project.yaml
   sap_profile: s4_private    ──► profiles/s4_private.yaml (yetenek matrisi)
   release: "2025"            ──► release_overrides["2025"]
   cleancore_policy: balanced ──► policy_axis["balanced"]
   master_language: TR        ──► ADR 0005-D (Z obje login dili + 4 label)
   source_root: SOURCE_CODES  ──► kaynak-kod klasörü adı
   frozen_readonly_paths      ──► pre_tool_guard yazma bloğu
```

Validator'lar, skill katmanı ve **MCP tool yüzeyi** profili okur. Profil alanları boşsa
varsayım yapılmaz: **tool yüzeyi kesilir** (Bölüm 10.6).

### 5.4 Sızıntı koruması — dört katman

| Katman | Nerede | Ne yakalar |
|---|---|---|
| ① Yazım anı | `pre_tool_guard` (Edit/Write core hedefi) | Core'a yazılan içerikte/dosya adında kimlik izi |
| ② Commit anı | `scripts/git-hooks/pre-commit` | Stage'lenen junction içeriği (`core/**`, `.claude/{agents,skills,commands,rules}/**`) |
| ③ Push/PR anı | CI `guard.yml → core-leak` | Aynı kontrolün sunucu-tarafı aynası |
| ④ Yayın anı | `pre_tool_guard` PUBLIC-PR gate | `gh pr create/edit/comment`, `issue create`, `release --notes`, `gh api …/pulls` gövdesinde kimlik izi |

Çekirdeğin kendi tarafında `core_precommit.py --all` (+ CI `gates` job) tam-ağaç tarar.
Desenler **tek kaynaktan** (`genericize_common.py`) gelir; kopya geri gelirse test kırar.

---

## 6. Enforcement Katmanı — Ne, Ne Zaman Tetiklenir

Ajan davranışı sohbet metniyle değil, `.claude/settings.json` içindeki **hook zinciriyle**
zorlanır. Hook'lar üç sonuç üretir: **exit 0** (sessiz geç), **stderr + exit 2** (bloklar),
veya **`additionalContext` JSON** (bağlam enjekte eder).

### Event → Hook haritası

| Event | Hook | Ne yapar | RED (exit 2)? |
|---|---|---|---|
| SessionStart | `session_start` | Yasak özeti + oturum protokolü enjekte; junction/drift/manifest/damga sağlığı | Hayır |
| SessionStart | `tooling_radar_check` | Tooling taraması bayatsa 1-satır nudge | Hayır |
| **InstructionsLoaded** | `instructions_loaded_log` | Hangi talimat dosyası ne zaman/neden yüklendi → `.tmp/instructions-loaded.log` | Hayır (yalnız log) |
| UserPromptSubmit | `skill_injector` | İş-türüne özel pre-flight checklist adını enjekte | Hayır |
| UserPromptSubmit | `intake_triage` | Geliştirme-talebi sinyali → ITG protokolü enjekte | Hayır |
| PreToolUse `Bash\|PowerShell\|mcp__sap-adt__*` | `pre_tool_guard` | 8 kural (aşağıda) | **Evet** |
| PreToolUse `Edit\|Write\|MultiEdit\|NotebookEdit` | `pre_tool_guard` | Core-leak + freeze + damga | **Evet** |
| PreToolUse `Edit\|Write\|MultiEdit` | `pull_before_edit` | SAP source bu seansta çekilmediyse edit'i blokla (ADR 0016) | **Evet** |
| PreToolUse `mcp__sap-adt__adt_(push_source\|activate\|…)` | `sap_worktype_hint` | **Gerçek obje-tipinden** deterministik checklist hatırlatması | Hayır |
| PreToolUse `mcp__sap-adt__*` | `itg_backstop` | SAP işi fiilen başladıysa ve ITG-marker yoksa protokolü enjekte | Hayır |
| PreToolUse `Agent` | `watchdog_launch` | Detached watchdog daemon başlat | Hayır |
| PostToolUse `Edit\|Write\|MultiEdit` | `post_validate` | Kural-taşıyan dosya editlendiyse `run_all_validators --quick` | **Evet** (FAIL'de geri besler) |
| PostToolUse `mcp__sap-adt__*` | `post_tool_failure` | Yapısal fail'de patinaj-kesici eskalasyon merdiveni | Hayır |
| ConfigChange | `config_change_guard` | Seans-içi davranış-yüzeyi değişimi manifest-onaysızsa blokla | **Evet** |
| PreCompact | `pre_compact` | SESSION_NOTES/memory flush hatırlatması | Hayır |
| SessionEnd | `watchdog_stop` | Watchdog daemon'ı kapat | Hayır |

### 6.1 Keşif vs güvence — 2026-07-09/10 redizaynı

İki mekanizma bilinçli olarak ayrıldı:

- **Keşif (hatırlama)** kırılgan prompt-keyword-regex'te değil, **native `description`
  semantiğinde** yapılır. Model karar verir, parafrazı yakalar. Bu yüzden ITG artık bir
  **skill**tir (`intake-triage`); regex hook yalnız erken hatırlatmadır.
- **Deterministik güvence** prompt-NLP'de değil, **tool sınırında** yapılır:
  `sap_worktype_hint` gerçek obje-tipini okur, `itg_backstop` ilk SAP tool'unda devreye girer.

> Ölçüm: eski regex hook, keyword-seti dışındaki 5 talebin 5'inde de ITG'yi hiç tetiklemiyordu.

### 6.2 `pre_tool_guard` — 9 kural (merdiven ilkesi)

2026-07-10 sağlık denetiminde guard 13 kuraldan 8'e indirildi; aynı gün 9. kural (GH-HEDEF)
eklendi. **Merdiven ilkesi:** runtime guard yalnız **geri alınamaz VE sessizce başarısız olan**
eylemler için meşrudur. Bir kural bu iki kriterden birini karşılamıyorsa statik kontrole
(validator / pre-commit / CI) iner.

| # | Kural | Neden runtime | Tetik |
|---|---|---|---|
| 1 | **KESİN YASAKLAR damgası** (ADR 0005) | Damga silinirse SESSİZ; anayasasız SAP yazımı | SAP-yazma tool'ları |
| 2 | **Bağlantı-tutarsızlığı** (ADR 0010) | Yanlış sisteme yazım GERİ ALINAMAZ, HTTP 200 SESSİZ | `mcp__sap-adt__*` |
| 3 | **Transport release** (ADR 0005-C) | GERİ ALINAMAZ, HTTP 200 SESSİZ | Bash / MCP argümanı |
| 4 | **PUBLIC-PR sızıntı gate** | Yayınlanan gövde cache'lenir (GERİ ALINAMAZ) | `gh pr/issue/release/api` |
| 5 | **Inline aktivasyon** | HTTP 200 sahte-OK (SESSİZ) | Bash |
| 6 | **Yalın fiori deploy** | "Successful" der, bayat `dist/` gider (SESSİZ) | Bash |
| 7 | **App-içi npm install** | Workspace ihlali | Bash |
| 8 | **GENERICIZE-LEAK** | Core PUBLIC; push'lanınca GERİ ALINAMAZ | Edit/Write core hedefi |
| 9 | **GH HEDEF BELİRSİZ** | `gh` hedefi **cwd'den** çıkarır; `core/` junction'dır → yanlış repoya yayın/mutasyon GERİ ALINAMAZ, `gh` başarı döner (SESSİZ) | Repoyu değiştiren `gh` alt-komutları |

Kural 9 üç grubu ayrı ele alır — çünkü `gh`'de hedef üç farklı yoldan verilir:

| Grup | Komutlar | Hedef nasıl açık olur | Cwd'ye düşer mi |
|---|---|---|---|
| **A** | `pr` · `issue` · `release` · `secret` · `variable` · `workflow` · `ruleset` · `label` | `--repo <O>/<R>` ya da `-R <O>/<R>` | Bayrak yoksa **evet** |
| **B** | `repo create/edit/rename/delete/archive` | Konumsal `<O>/<R>` (bayrak yok) | Argümansızsa **evet** |
| **C** | `api` | Yolun kendisi (`repos/<O>/<R>/…`, `orgs/<O>/…`) | Yalnız `{owner}`/`{repo}` **placeholder** varsa |

Okuma komutları (`list`/`view`/`status`) ve repo-hedefsiz API'ler (`gh api user`, `graphql`,
`rate_limit`) **kapsam dışıdır** — kural gürültü üretmez.

> **Kural 9 nasıl doğdu ve iki kez nasıl yakalandı.** Bir PR `--repo` verilmeden açılmaya
> çalışıldı; guard görünürlüğü soramayınca fail-closed reddetti. Asıl tehlike ise fark
> edilmemişti: yanlış cwd'de (ör. `core/` junction'ı içinde) çalışan bir `gh pr create`,
> private proje içeriğini public çekirdeğe yayınlayabilirdi.
>
> Kural konurken **iki hata yaptı ve ikisini de sistem yakaladı.** (1) `guard_conformance`
> ④ vakası bir yanlış-pozitif buldu: desen komut-başı çapası taşımadığı için
> `git commit -m 'gh pr create …'` **mesajını** komut sanıyordu. (2) Regresyon taraması
> dört kırılma gösterdi: `gh api user` / `graphql` / `rate_limit` ve `gh repo create <O>/<R>`
> — yani `PROJECT_BOOTSTRAP` STEP 1'in kendisi. İlk model `gh api`'nin `--repo` bayrağı
> olmadığını ve `gh repo create`'in hedefi konumsal aldığını gözden kaçırmıştı.
>
> Ders: **runtime guard eklerken önce blast-radius ölçülür.** Kural doğru, model yanlıştı.

**Kaldırılan 4 kural** ve gerekçeleri (her biri ayrı ölçüldü): freeze-guard (git-remote'ta
yedekli → geri alınabilir; ayrıca 6 kabuk-yolundan sızıyordu), özyinelemeli-silme bloğu
(geri alınabilir ve sessiz değil), sızıntı-commit kilidi (iki ikizi var: validator + CI),
`applies_to` eksikliği (yalnız `Write`'ı tutuyordu → yarım koruma).

> **Kabul edilen kalıntı:** guard, `echo >> core/f.md` / `cp` / `tee` gibi kabuk kaçışlarını
> kapatmaz (komut-metni regex'i sonsuz varyant savaşıdır). Telafi katmanı pre-commit + CI'dır.
> Bu bilinçli bir merdiven tasarımıdır; `guard_conformance.py` guard yüzeyini beyan eder.

### 6.3 Guard'ın kendi meta-gate'i

`scripts/tests/guard_conformance.py`: her kural için **③ tetiklenmeli** ve **④ tetiklenmemeli**
vakaları + kablolama + grup kontrolü. Kanıtsız kural CI'yı kırar. `test_pre_tool_guard.py`
ayrıca desen **tek-kaynak** değişmezini ve `gh` yayın yüzeyini (13 vaka) zorlar.

---

## 7. Kalite Kapıları: Validator + Reviewer + Coverage

| | `run_all_validators.py` | `run_review.py` |
|---|---|---|
| Amaç | Repo-geneli sağlık taraması | Tek SAP-yazma işi öncesi pre-flight |
| Kapsam | Tüm proje (kural-taşıyan artefaktlar) | Belirli `--task` + `--artifact` |
| Ne zaman | Oturum-başı `--quick`, `post_validate`, **pre-commit**, CI | SAP'a create/push/activate ÖNCESİ |
| Çıktı | OK / N ihlal (exit 0/1) | PASS / WARNING / BLOCKER |

`run_all_validators.py` iki modda koşar. **PROJE modu** (`project.yaml` var): scope=project+both
validator'lar + profil filtreleri + `validators-local/*` keşfi. **CORE modu** (project.yaml yok,
ör. DEV_CORE CI): yalnız scope=both statik validator'lar.

### Kayıtlı gate zinciri (22)

KESİN YASAKLAR damgası (ADR 0005) · Core-sızıntı kilidi (R1) · Paket `.rules.md` varlık ·
Paket naming · Obje paket sınırı · Script playbook referansı · Freestyle UI5 tuzaklar ·
Liste=grid (ADR 0008) · Filtre/VH deseni (FE-32) · RAP BY-assoc keys-only (BE-20) ·
RAP commit yasağı (BE-26) · AMDP yorum-apostrof (BE-28c) · KD ham-mermaid (DOC-KD-15) ·
Proje-kökü çözümlemesi (CORE-01) · **Kural↔gate coverage (ADR 0019)** · Hook enjekte-yol
çözümlemesi (C-HOOK-01) · CORE-INDEX tazeliği (C-IDX-01) · Konsol UTF-8 koruması (C-ENC-01) ·
**Auto-memory bütçe + indeks bütünlüğü (C-MEM-01)** · **package-registry tazeliği (C-REG-01)** ·
**settings.template ↔ hook envanteri (C-TPL-01)** · Playbook freshness (uyarı)

Ayrıca **C-DOC-01** (docs aynası ↔ `core/docs`) projede `docs/` varsa koşar.

Son dördü 2026-07-10'da eklendi; her biri gerçek bir sessiz-bozulmayı kapatır:

- **C-MEM-01** — hafıza indeksi sessizce kesiliyordu (Bölüm 11.2).
- **C-REG-01** — `manual-edit: PROHIBITED` diyen artefaktın tazeliğini kimse ölçmüyordu.
- **C-TPL-01** — yazılan hook şablona kablolanmıyordu (Bölüm 3, 16.2).
- **C-DOC-01** — çoğaltılmış belge tazelik kontrolü olmadan drift üretir.

> **Bypass'a zorlayan gate, gate değildir.** C-DOC-01 CI'da **WARNING**, lokalde **HARD**'dır.
> Sebep: CI checkout'unda `core/` junction'ı yoktur, DEV_CORE **main** klonlanır; bir ayna PR'ı
> kaynağı merge edilene kadar **zorunlu olarak** bayat görünür. Bu, gate'i kalıcı kırmızı yapar
> ve `--admin` bypass'ını normalleştirir. Otorite **lokal pre-commit**'tir (gerçek junction).
> Aynı gerekçe `CORE-INDEX` (C-IDX-01) için de geçerlidir ve orada da CI çapraz-repo
> staleness'i yapısal olarak zorlamaz.
>
> *Bu kural, kendisi bir bypass'a yol açtıktan sonra yazıldı:* ayna PR'ının `validators` job'u
> kırmızıydı ve `--admin` ile merge edildi. İçerik doğruydu (kaynak 53 saniye sonra merge
> oldu), ama süreç yanlıştı.

### `run_review.py` (ADR 0006)

`TASK_VALIDATORS` sözlüğü her görev-tipini bir validator zincirine ve severity'ye eşler:

```text
cds_creation      → window_function(BLOCKER) + currency_ref(BLOCKER) + released_objects(WARNING) …
table_update      → struct_field_dtel_active(BLOCKER) + table_field_drop(BLOCKER) …
class_push        → method_param_type_c(BLOCKER) + amdp_apostrophe(BLOCKER) + abaplint(WARNING) …
rap_bdef_creation → rap_managed_etag(BLOCKER) + audit_fields_autofill(WARNING)
itg_s2_signoff    → check_itg_signoff(BLOCKER)            ← ITG S2 gate (ADR 0022)
```

```text
BLOCKER > 0 → verdict BLOCKER → SAP yazma YASAK (exit 1)
WARNING > 0 → verdict WARNING → yazabilirsin AMA kullanıcıya bildir (exit 0)
aksi        → verdict PASS
--strict    → WARNING'i de BLOCKER say
```

### `check_rule_gate_coverage.py` (ADR 0019 — "keystone")

*Her kural bir gate'le zorlanmalı; gate'lenmemiş kural ≈ kuralsızdır.*

```text
3-EKSEN:  (a) gate dosyası VAR mı
          (b) bir runner'a WIRED mı (run_all / run_review)
          (c) kırmızı-fixture ile test ediliyor mu

Bulgu sınıfları:
  MISSING    — checklist gate adı verir ama dosya YOK (en ciddi: sahte-WIRED)
  ORPHAN     — script VAR ama hiçbir runner'da DEĞİL
  UNDECLARED — WIRED ama `# ENFORCES:<id>` beyanı yok
```

**Kritik ilke — "sürekli PASS kanıt değildir":** bir gate yanlış-kablolanmış veya no-op
olabilir. Her gate kasıtlı bozuk bir fixture'la (kırmızı-girdi) FAIL üretebildiği doğrulanarak
kabul edilir. (Operasyonel karşılığı: Bölüm 14.3.)

---

## 8. Kural Mimarisi (L1–L4) ve SORU 0

| Katman | Konu | Yer | **Nasıl yüklenir** |
|---|---|---|---|
| **Anayasa** | KESİN YASAKLAR (A/B/C/D) | kök `CLAUDE.md`, fiziksel damga | Her oturum; `/compact` sonrası diskten yeniden enjekte |
| **L1a** | Her-oturum davranış değişmezleri | `CLAUDE.core.md §1.1` | Her oturum (`@import`) |
| **L1b** | Dosya-türüne bağlı davranış | `claude/rules/*.md` | **Eşleşen dosya okununca** (`globs:`) |
| **L1c** | Derin davranış referansı | `AGENTS.md` | ⚠ **Otomatik YÜKLENMEZ** |
| **L2** | Stabil kurumsal standartlar | `standards/` | On-demand |
| **L3** | Operasyonel pattern | `playbook/` | On-demand |
| **L4** | Paket-spesifik | `<source_root>/<MOD>/<PKG>/.rules.md` | On-demand |

### 8.1 Neden bu bölünme (ölçülmüş gerekçe)

`AGENTS.md` bir markdown link'in arkasındaydı ve **hiç yüklenmiyordu**. Harness `CLAUDE.md`
okur, `AGENTS.md` okumaz. 356 satır / 25 zorunlu kural sessizce ölüydü; ekran teyidi ise her
oturum "yüklendi" diyordu. Çözüm:

- Her oturum gereken (git workflow, subagent kararı, STOP kuralı, bağlantı) → **L1a**.
- İş-anına özgü olan (ADT işlem sırası, reviewer pre-flight, dosya yerleşimi, UI5 tuzakları)
  → **L1b**, `globs:` ile ilgili dosya okununca yüklenir. Startup maliyeti sıfırdır.
- Derin referans → **L1c**, açıkça okunur.

### 8.2 `claude/rules/` yazım kuralları — bir tuzak

**`globs:` kullanılır, `paths:` KULLANILMAZ.** Resmî doküman `paths:` (YAML listesi, tırnaklı)
tarif eder ama o biçim **sessizce çalışmaz** — hata vermez, kural hiç yüklenmez. Çalışan biçim
tırnaksız, virgülle ayrılmış tek satırdır:

```yaml
---
globs: **/*.abap, **/*.ddls
---
```

`globs:` **olmayan** kural koşulsuz yüklenir (her oturum). **Compaction uyarısı:**
`globs:`-scoped kurallar `/compact` sonrası kaybolur (eşleşen dosya tekrar okununca döner).
Bu yüzden **anayasa buraya konmaz** — kök `CLAUDE.md`'ye fiziksel damgalıdır (ADR 0021) ve
compaction'dan sağ çıkan tek yerdir.

### 8.3 SORU 0 — yeni bilgi nereye yazılır

```text
SORU 0: Bu bilgi metodoloji mi, projeye mi özel?
  ├─ Metodoloji (pattern, validator, hook, standart, ADT dersi, checklist satırı)
  │     → DOĞRUDAN core'a yaz. Yazarken:
  │       • genericize: gerçek obje/sistem/kullanıcı/müşteri → placeholder
  │       • link: core-içi link CORE-göreli; core → proje link YASAK
  │       • profil etiketi: applies_to hangi profiller? (kanıtsız genişletme YOK)
  └─ Proje işi (paket, iş kuralı, müşteri süreci, bağlantı, sprint)
        → proje reposu (L4 .rules.md aynen)

SORU 1: Tek paket mi, tüm proje mi?   → tek paket = L4
SORU 2: Tipi? davranış=L1a/L1b · standart=standards · nasıl-yaparım=playbook · karar=decisions
SORU 3 (L3): dar obje-tipi → playbook/adt-<tip>.md · cross-cutting → lessons-learned.md
```

Ek dal (2026-07-10): bir kural **dosya-türüne bağlıysa** (yalnız `.abap` ya da `ui/**` işinde
geçerli) → `claude/rules/` + `globs:`. Bir playbook girdisi **çok-adımlı prosedüre** dönüştüyse
→ skill.

### 8.4 T1–T11 tetikleri

| # | Tetikleyici | Hedef |
|---|---|---|
| T1 | ADT işlemi başarısız denemelerden sonra başarılı oldu | `playbook/<obje-tipi>.md` (çalışan + denenen-başarısız) |
| T2 | Playbook'ta olmayan senaryo başarıyla işlendi | Yeni section `playbook/` |
| T3 | Kullanıcı kural koydu | Davranış → L1a/L1b; standart → `standards/`; pakete özel → `.rules.md` |
| T4 | Kullanıcı trigger-phrase kullandı | `lessons-learned.md` + kod gate öner |
| T5 | Yeni paket / naming kararı | `.rules.md` (bootstrap script) |
| T6 | TempScripts'te çalışan script kalıcı lazım | core `scripts/`e taşı (genericize) + playbook ref |
| T7 | Mimari karar | Metodoloji → core `governance/decisions/`; proje → proje reposu |
| T8 | Paket-spesifik istisna | `.rules.md` "Bilinen İstisnalar" |
| T9 | Script kullanıldı ama playbook referansı yok | İlgili playbook'a pattern + script ref |
| T10 | Patinaj/hata yakalandı | Düzelt + playbook (T1) + "reviewer yakalar mıydı?" |
| T11 | Tekrar-eden tuzak / yeni iş-türü | validator / checklist / hook / pre_tool_guard (playbook notu YETMEZ) |

### 8.5 Kural nasıl eklenir (ADR 0019 onboarding)

```text
(1) GÜÇ-ETİKETLE      — MUST / MUST-NOT / SHOULD / MAY
(2) ENFORCEMENT-SEÇ   — otomatikleştirilebilir mi, yargı mı?
(3) BAĞLA             — gate + kırmızı-fixture VEYA reviewer + checklist-üyeliği
(4) STABİL-ID VER     — kural-id (FE-32, BE-26, C-MEM-01…) + gate `# ENFORCES:<id>` beyanı
(5) COVERAGE-CHECK    — check_rule_gate_coverage temiz mi
```

---

## 9. İş-Alım: Intake Triage Gate (ITG)

ITG (ADR 0022) bir geliştirme talebinin alım-sürecini standartlaştırır: kapsamına orantılı,
kişiden bağımsız, kanıtlı. Çekirdek ilke: ajan her domain'i ezbere bilmez — iş geldiğinde onu
**sınıflar → isterlerden bilmesi gereken konuları çıkarır → hedefli araştırır → ancak
bilgilendikten sonra** değerlendirir.

### 9.1 Üç katmanlı tetikleme (redizayn)

```text
① native skill `intake-triage`   → SEMANTİK keşif; parafrazı yakalar ("bu ekrana kolon koyalım")
② intake_triage hook (regex)     → erken hatırlatma; kırılgan, tek başına yeterli DEĞİL
③ itg_backstop (PreToolUse)      → ilk SAP tool'unda ITG-marker yoksa protokolü DETERMİNİSTİK enjekte
```

Eski kurgu yalnız ② idi ve keyword-seti dışındaki talepleri hiç yakalamıyordu.

### 9.2 İki dik eksen

```text
① Fonksiyonel modül ekseni (NE iş?)  : SD / MM / FI / CO / PP / QM / PM / WM-EWM
     → modül kural-paketi (playbook/modules/<kod>.md) varsa OKUnur
② Teknik/kodlama-tipi ekseni (NASIL?) : klasik ABAP / RAP / Fiori-UI5 / CDS / DDIC
     → obje-tipi checklist'i + standardı zaten enjekte edilir
```

**Persona = kural-paketi, "act as X" DEĞİL.** Uzmanlık kaynak-zincirinden çıkar,
persona-placebo'dan değil.

### 9.3 6 adımlı protokol

```text
1. SINIFLA — iki dik eksen + KAPSAM (S0/S1/S2); gerekçeyi bir cümleyle yaz
2. Modül kural-paketini OKU
3. İSTERLERDEN KONU ÇIKAR ("kullanılabilir stok" → availability/ATP)
4. 3-EKSEN ARAŞTIR:
     (a) domain bilgisi (resmî kaynak; syntax TAHMİN EDİLMEZ)
     (b) canlı sistem / ilişkili kod (where_used + package_contents → harita, sonra adt_get)
     (c) kurumsal hafıza / prior-art (memory + lessons-learned + SESSION_NOTES)
5. KANITLI DEĞERLENDİR — reuse + tutarlılık + geçmiş-ders + risk; TAHMİN YASAK
6. KAPSAM-ORANTILI SORU + AKSİYON
```

Kalite kilidi: bir Z-obje hatırlanıyorsa **canlı doğrula** (hafıza = hipotez, canlı = otorite);
prior-art "sanırım yaptık" değildir — referansı bul + doğrula, yoksa "yok" say.

### 9.4 Kapsam sınıfları

| Sınıf | Nedir | Akış ağırlığı |
|---|---|---|
| **S0 · nokta-düzeltme** | tek alan/label/mesaj; davranış değişmez | HAFİF: where-used → fix → bug-gate |
| **S1 · lokalize** | tek app/rapor/CDS içi davranış değişimi | ORTA: kısa etki analizi + hedefli soru |
| **S2 · kapsamlı** | yeni program / çok-obje / cross-stack | TAM: intake-artefaktı + mutabakat |

Over-triage (küçük işe ağır süreç) de anti-pattern'dir.

### 9.5 S2 sign-off gate

S2 iş, SAP yazımına geçmeden sabit-şemalı bir **intake-artefaktı** üretir ve kullanıcı
mutabakatı alır. `check_itg_signoff.py` deterministik doğrular (severity BLOCKER):
zorunlu alanlar dolu mu, `prior-art` alanı `bulundu:<ref>` veya `yok` içeriyor mu (boş
bırakılamaz), `MUTABAKAT` satırında `[x]` var mı. Kabul kriterleri EARS kalıplarıyla yazılır.

---

## 10. SAP ADT MCP Sunucusu

`stdio` transport'lu typed tool katmanı (ADR 0007): tek-obje işlemleri serbest-metin shell
komutu yerine, dönüşü yapısal JSON (`{ok: bool, …}`) olan ve guardrail'i **sunucu tarafında**
zorlayan araçlarla yapılır.

### 10.1 Tool envanteri (19)

| Grup | Tool | Yazma? |
|---|---|---|
| **Okuma / Analiz** | `ping` · `adt_get` · `adt_search_objects` · `adt_where_used` · `adt_table_read` · `adt_package_contents` · `adt_lock_check` · `adt_transport_list` · `adt_syntax_check` · `adt_atc_check` | Hayır |
| **Yaratım / DDIC** | `adt_post_shell` · `adt_domain_create` · `adt_dtel_create` · `adt_struct_create` | Evet |
| **Aktivasyon / Push** | `adt_push_source` · `adt_activate` · `adt_delete` | Evet |
| **Servis / Yürütme** | `adt_publish_service` · `adt_classrun` | Evet |

Okuma tool'ları hiçbir koşulda yazmaz; bu ayrım ajan tool-allowlist'lerinde fiziksel
enforcement'ın temelidir (Bölüm 12.1).

### 10.2 Sunucu tarafı guardrail'ler (hardcoded, bypass yok)

| ADR | Kural | Uygulama |
|---|---|---|
| **0005-A** | Standart obje yaratma/silme yasak — Z/Y namespace zorunlu | `require_customer_namespace`, `reject_standard_delete` |
| **0005-C** | Transport zorunlu; asla varsayılmaz | `require_transport` |
| **0005-D** | Z obje `master_language` text zorunlu; DTEL 4 label dolu | `require_tr_text`, `require_all_labels` |
| **0010** | Mutasyon yalnız DEV tier'da; QA/PRD salt-okunur | `require_writable_tier` |
| **0011** | QA/PRD'de hassas tablo/alan okuma açık onay ister (KVKK) | `require_data_access` |

Ek iki **bağlam-tutarlılık backstop'u**: `_guard_binding_current` (`.conn_adt` değişip
`/mcp restart` edilmediyse ADT işlemini reddeder — "write DEV der, istek QA'ya gider"
felaketini önler) ve `_guard_module_current` (bayat kodu bellekte çalıştırıyorsa reddeder).

### 10.3 Composite create + readback ("activated" yalanına karşı)

Bir yazımın "ok" dönmesi, objenin gerçekten **aktif ve doğru içerikle** oturduğu anlamına
gelmez.

- **Composite atomik akış** (`adt_*_create`): guardrail → pre-check → create → activate →
  **verify** (`adtcore:version="active"`). *Varlık kanıt sayılmaz* (`existence != active`).
  Activate başarısızsa obje inactive bırakılır, otomatik silinmez.
- **Readback-gate** (`adt_push_source` + `adt_activate`): push edilen source `(ad, tip)`
  anahtarıyla tutulur; activate sonrası **aktif** source çekilip normalize-karşılaştırılır.
  Fark varsa `content_verified=False` + `ok=False`. Yalnız isimle key'lemek DDLS/BDEF
  çakışmasında sahte-mismatch üretir.

### 10.4 Reviewer pre-flight (ADR 0006)

Yazma tool'ları source'u geçici dosyaya yazıp `run_review.py`'ı otomatik çağırır. BLOCKER ise
push reddedilir; WARNING geçer ama yanıta `reviewer` alanı eklenir. Tablo DROP'ları için
`ack_drop` hedefli/denetlenebilir alternatiftir.

### 10.5 MCP-vs-script karar kuralı

| İş türü | Kanal | Gerekçe |
|---|---|---|
| Tek obje yaratım/aktivasyon/push/silme/arama/where-used/lock/table-read | **MCP tool** | Typed dönüş + sunucu-tarafı guardrail + readback |
| CSV/batch, validator koşumu, sprint/spec gate'leri | **Script** | Toplu-işlem + orkestrasyon |

### 10.6 Profil-bazlı tool yüzeyi (D34d)

Tool'lar `available_on` etiketi taşır. Profil uymuyorsa tool **hiç register edilmez** →
`tools/list`'te görünmez. Model olmayan bir tool'u çağıramaz.

```text
sap_profile: s4_private  →  19 tool
sap_profile: btp_abap    →  18 tool  (adt_transport_list gizli: transport=gcts, CTS ucu yok)
sap_profile: yok/geçersiz →  1 tool  (yalnız ping — FAIL-CLOSED)
```

> **Kanıt disiplini.** Politika tablosu kısadır çünkü `profiles/*.yaml` kendi başında
> *"matris rehberdir, kanıt değildir"* der. Bugün tartışmasız tek matris-hücresi
> `btp_abap.transport: gcts`'tir. `s4_public.transport` hücresi açıkça "NÖTR, canlı
> doğrulanacak" dediği için **bloklanmaz**. Tablo, ilk `s4_public`/`btp_abap` projesinde canlı
> testle genişletilir. Bu tembellik değil, kanıt yokluğudur.

---

## 11. Kurumsal Hafıza (Memory) Sistemi

Temel ilke: **memory = hatırlatıcı, core = kanonik.**

### 11.1 Memory türleri

| Tür | Konum | İçerik |
|---|---|---|
| **user** | `~/.claude/CLAUDE.md` | Projeden-bağımsız kişisel tercih (metodoloji YAZILMAZ) |
| **feedback** | proje memory klasörü + `MEMORY.md` | Davranış/çalışma-disiplini kuralları |
| **project** | proje memory klasörü + `MEMORY.md` | Projeye-özel work-state (iş çapaları, kararlar) |
| **reference** | `MEMORY.md` altında | Sabit başvuru bilgisi |

Proje memory'si repo DIŞINDADIR (`~/.claude/projects/<slug>/memory/`) ve **makine-lokaldir** —
başka geliştiriciye akmaz. Bu, metodoloji-nitelikli memory'nin core'a terfi etmesini zorunlu
kılar (11.4).

### 11.2 Sert sınır: 200 satır **veya** 25 KB

`MEMORY.md`'nin yalnız **ilk 200 satırı veya ilk 25 KB'ı** (hangisi önce gelirse) oturum
başında yüklenir. Gerisi **yüklenmez, uyarı verilmez.** Türkçe metinde bağlayıcı kısıt genelde
**bayt**tır (çoğu harf 2 bayt).

Sonuçlar:

- Kesilme **sondan** olur → davranış kuralları (`## Feedback`) indeksin **üstünde** durur,
  proje durumu (`## Project`) altta.
- Konu dosyaları (`feedback_*.md`, `project_*.md`) startup'ta **yüklenmez**; ihtiyaç anında
  okunur. Bu doğru mimaridir — indeks ince kalmalıdır.
- **Gate C-MEM-01** (`check_memory_index.py`): bayt/satır doluluğu (%85 WARNING, %95 FAIL),
  ölü indeks linki, indeksten erişilemez hatıra, frontmatter şeması. `memory-seed`'i de kapsar.

### 11.3 memory-seed (yeni proje tohumu)

`claude/memory-seed/` (85 `feedback_*.md` + `MEMORY.md`) yeni geliştiricinin proje-hafıza
klasörüne `seed_memory.py` ile tohumlanır. Kapsam yalnız **feedback**tir; projeye-özel
work-state tohuma dahil değildir.

Merge-safe: hedefte var olan dosya ezilmez. **Rename/silme uzlaştırması** (2026-07-10):
`.seed-manifest.json` tohumlanan adları ve hash'lerini tutar. Seed'de bir dosya yeniden
adlandırılınca (ör. kimlik sızdıran ad temizlenince) eski dosya + bayat indeks satırı artık
tespit edilir; eksik indeks satırları eklenir, ölü linkler düşer, **kullanıcı dokunmamış**
tohum dosyaları `--prune` ile silinir. Manifest yoksa hiçbir şey silinmez, yalnız uyarılır —
*yaratmadığımız dosyayı silmeyiz.*

### 11.4 Terfi mekanizması (metodoloji → core, pointer kalır)

Bir memory-feedback metodoloji-nitelikliyse core'a **terfi eder**; memory'de tek-satır pointer
kalır. Yön kararı SORU 0 ağacıyla verilir. Terfi, memory'nin makine-lokal olması nedeniyle
ekip-ölçeğinde zorunludur.

### 11.5 Alt-ajanlar auto-memory'yi GÖRMEZ

Bir alt-ajan (subagent) kendi context penceresiyle başlar: `CLAUDE.md` kopyasını alır,
**ana oturumun auto-memory'sini almaz.** Yani lider'in birikmiş dersleri alt-ajanda yoktur.

Bu yüzden altı ajan tanımının başına *"sen auto-memory görmezsin + kanıt kuralları"* bloğu
fiziksel olarak yazılmıştır: TAHMİN YASAK · kanıtsız iddia yazma · bulunamadı ≠ yok ·
kod ≠ kablolama · çökme ≠ FAIL · erişemediğini "DOĞRULANAMADI" işaretle ·
`SendMessage({to:"main"})` ile raporla.

> Ölçülmüş tezahür: bir araştırma alt-ajanı, hiçbir kaynakta bulunmayan bir başarı yüzdesi
> üretti ve resmî dokümana 404 alınca çıkarımı kanıt diye sundu. Kural brifingde yazılmamıştı.

### 11.6 Oturum-sürekliliği artefaktta yaşar

Süreklilik ajanların canlı bağlamında değil, kalıcı artefaktlarda yaşar (repo kaynağı, SAP
objeleri, `SESSION_NOTES.md`, memory, git). *"Aklımda tutarım"* geçerli bir süreklilik
mekanizması değildir.

---

## 12. Çok-Ajanlı Çalışma Modeli

Takım okuma/araştırma-ağırlıklı, gerçekten paralelleşen iş için açılır; seri/bağımlı iş solo
yürütülür. Uzmanlaştırma persona değil **grounding**'dir (zorunlu pre-flight okuma + kanonik
desen pointer + scoped tool + skill).

### 12.1 Roller ve tool-düzeyi yetki ayrımı

| Rol | Lifecycle | SAP yazma | Görev |
|---|---|---|---|
| **lider** (ana oturum) | daimi | Koşullu (12.2) | Orkestrasyon, kullanıcı muhatabı, **tek committer** |
| **adt-gateway** | STANDING | ✅ TEK yazıcı | Takım modunda tüm SAP yazımı |
| **backend-expert** | LAZY | ❌ | ABAP/RAP/CDS/DDIC; tasarım + yerel kaynak + read-only |
| **frontend-expert** | LAZY | ❌ | Freestyle UI5 / OData V2 |
| **bug-expert** | LAZY + her review TAZE | ❌ | Adversarial inceleme; PASS/WARNING/BLOCKER |
| **sap-feature / sap-research** | LAZY | ❌ | Feature sahipliği / salt-okunur araştırma |

Yetki ayrımı **tool-allowlist ile fiziksel**tir, hook ile değil (hook çağıran-ajanı ayırt
edemez). Expert'lerin allowlist'inde `adt_push_source`, `adt_activate`, `adt_*_create`,
`adt_delete`, `adt_post_shell`, `adt_classrun` **yoktur**.

### 12.2 Single-writer (koşullu serializasyon)

- **Solo:** lider SAP'ye doğrudan yazar (run_review pre-flight + ADR 0005 yine geçerli).
- **Takım aktif:** tüm SAP yazımı `adt-gateway`'den geçer. Ortak objeler lider tarafından
  sıralanır; paralel ALTER yaptırılmaz.

### 12.3 Bug-gate (expert → bug-expert → lider)

1. Expert build'i bitirince lider'e `BUG_GATE_READY` + diff + niyet + blast-radius yollar.
2. Lider **TAZE** bir bug-expert spawn edip diff'i besler (önceki bug context'i kirlilik).
3. Verdict: PASS → lider commit; BLOCKER/EKSİK → Expert yeniden devreye alınır.

Bulgu tipi üçlüdür: **HATA** (kod bozuk) / **EKSİK** (must-do karşılanmamış) / **ÖNERİ**
(bağlayıcı değil). bug-expert read-only'dir → "düzeltilmeli" der, fix'i Expert yapar.

### 12.4 İletişim ve süreklilik

Lider = hub. Ajan brifingine `SendMessage({to:"main"})` eklenmezse rapor gelmez. Alt-ajanların
memory körlüğü (11.5) nedeniyle kanıt kuralları brifingde **tekrar edilir**.

---

## 13. GitHub Mimarisi ve Çalışma Akışı

### 13.1 Repolar

| Repo | Görünürlük | Rol |
|---|---|---|
| `<ORG>/DEV_CORE` | **public** | Canlı metodoloji çekirdeği — junction'la tüm projelere yansır |
| `<ORG>/template_project` | **public** | Referans iskelet (gerçek SAP bağlantısı yok) |
| `<ORG>/<PROJE_REPO>` | private | Proje reposu — SAP kaynağı, docs, project.yaml, governance |

Core'un public olması genericize disiplinini **zorunlu** kılar: müşteri/sistem/kullanıcı adı,
gerçek Z-obje adı core'a giremez (Bölüm 15.2).

### 13.2 Ruleset'ler ve stable-tag

| Ruleset | Kapsam | Etki |
|---|---|---|
| `main-pr-required` (active) | `main` | Doğrudan push yasak; branch → PR → CI yeşil → merge; 1 onay |
| `stable-tag-lider-only` | CORE `stable` tag | Tag'i yalnız lider ilerletir |

> ⚠ **Tek-geliştirici tuzağı.** `bypass_actors = [OrganizationAdmin, bypass_mode: pull_request]`
> ayarı, org admin'in kuralı **yalnız PR üzerinden** atlamasına izin verir; doğrudan push yine
> reddedilir. Ama GitHub **kendi PR'ınızı onaylatmaz**. Tek code-owner varsa her merge bir
> `--admin` bypass'ı olur ve "1 onay zorunlu" kuralı fiilen hiçbir onay kaydetmez. Bu durumda
> ya ikinci bir reviewer eklenir, ya `required_approving_review_count=0` yapılıp gerçek koruma
> `required_status_checks`e bırakılır (CI bypass edilemez).

### 13.3 CI

**Proje `guard.yml` — üç job:**

- `core-leak`: tracked tree'de `core/**` veya `.claude/{agents,skills,commands,rules}/**`
  görülürse FAIL.
- `validators`: CI checkout'unda `core/` yoktur (junction) → DEV_CORE (public) klonlanır,
  `CORE-INDEX` yeniden üretilir, `run_all_validators.py` koşar. *Bu job yoksa validator'ların
  çoğu yalnız elle çalışır.*
- `behavior-surface`: davranış-yüzeyi dosyaları PR'da dokunuluyorsa görünür WARNING;
  `main`'e **merge-olmayan doğrudan push** dokunuyorsa FAIL. Squash-merge'ler yanlış-tetiklemesin
  diye commit'in merged-PR'dan gelip gelmediği `gh api commits/{sha}/pulls` ile sorulur
  (bu yüzden `permissions: pull-requests: read` şarttır).

**CORE `core-ci.yml` — `gates` job:** `core_precommit.py --all` (tam-ağaç genericize + link-audit
+ applies_to) + `run_all_validators.py` + `py_compile` + guard konformans testleri.

> **Fail-closed genericize.** Kimlik blocklist'i repo ağacının DIŞINDA yaşar
> (`.git/genericize-blocklist`) — çünkü müşteri adını public bir filtreye yazmak, engellenmeye
> çalışılan sızıntının kendisidir. Ama `.git/` klonlanmaz: CI taze klon yaptığı için liste hiç
> yüklenmiyordu ve public repoya giden son kapı **kördü**. Artık liste `IX_GENERICIZE_BLOCKLIST`
> repository secret'ıyla verilir; yoksa `--all` modunda gate **durur**.

### 13.4 Rollback (stable-tag + detached)

`stable` = bilinen-iyi commit. Core bir hatayla oturumu bloke ederse `git -C <core> checkout
stable` → tüm projeler anında bilinen-iyiye döner (session_start bunu "detached@stable" olarak
sakin raporlar). Junction'a dokunulmaz — rollback tamamen git işlemidir.

### 13.5 Davranış-yüzeyi güvenlik duvarı

Davranış taşıyan dosya ya core'dan junction'la gelir ya behavior-manifest'te kayıtlıdır.
Yabancı repoya ilk temas: Claude'suz `foreign_project_audit.py` pre-scan → `--safe-mode` →
kod-sınıfı (hooks/MCP) incelemesiz normal oturum açılmaz → `guest_mode.py`.

---

## 14. Sağlık ve Kalite Araçları

### 14.1 `ix_doctor` (7 katman)

| # | Katman | Örnek kontroller |
|---|---|---|
| 1 | FS + bağımlılık | junction'lar gerçek core'a çözülüyor · plugin envanteri · CLI mevcudiyeti |
| 2 | Git | remote org tutarlı · `main == origin/main` · `stable` tag · hooksPath · tree temizliği |
| 3 | GitHub-enforce | ruleset ACTIVE · CI yeşil · repo tree'de core-sızıntısı yok |
| 4 | Claude katmanı | settings/shim template-drift (hash) · behavior-manifest ↔ ağaç · hook smoke · guard CANLI test |
| 5 | MCP / SAP | `.conn_adt` var + placeholder'sız · MCP server erişilebilir · (`--live-sap`) canlı probe |
| 6 | Validators + perf | `run_all_validators` TAM PASS + süre · `session_start` < 1.5 sn |
| 7 | İş-akışı smoke | memory dolu · deploy-zinciri import-sağlığı · aktif paket `.rules.md` |

Exit 0 = FAIL yok. SAP'ye default'ta **asla** çıkılmaz (`--live-sap` gerekir).

### 14.2 `behavior_manifest` (davranış-yüzeyi hash envanteri)

Proje-lokal davranış dosyalarının (`CLAUDE.md`, `.mcp.json`, `project.yaml`, `hook_shim.py`,
`.claude/settings*.json`) SHA-256 envanteri. Yalnız lider-onaylı PR ile güncellenir
(`generate`); `session_start` her oturum canlı ağacı manifest'le karşılaştırır. Junction'la
gelen core içeriği manifest DIŞIDIR — onun bütünlüğü core-git'in işidir.

### 14.3 Enforcement-testi (guard'ları bozuk-girdiyle sınama)

Sürekli PASS dönen bir kontrol, bir şeyi zorladığının kanıtı değildir.

- `guard_conformance.py` — her kural için ③ tetiklenmeli / ④ tetiklenmemeli + kablolama +
  meta-gate. Kanıtsız kural CI'yı kırar.
- `test_pre_tool_guard.py` — sızıntı deseni tek-kaynak değişmezi, `gh` yayın yüzeyi (13 vaka),
  blocklist birleşimi.
- `ix_doctor` katman 4 — guard'a sahte-Write stdin-JSON'u simüle eder (gerçek yazma YOK),
  exit 2 + RED mesajı bekler; hem backslash hem forward-slash varyantıyla.

> **Tarihsel not.** Guard'ın eski canonicalize hâli bir yol varyantında sessizce yanlış-pozitif
> PASS veriyordu. Ve `pre_tool_guard`'ın PowerShell matcher'ı eksikti: Bash'te bloklanan komut
> PowerShell'den geçiyordu. Kod-seviyesi koruma, **kablolanmadan** koruma sanılır.

---

## 15. Güvenlik, Gizlilik ve Uyumluluk

### 15.1 Veri gizliliği (KVKK) — PII guard
`adt_table_read` sistem katmanına duyarlıdır (ADR 0011): DEV'de serbest; QA/PRD'de hassas
tablo/alan (müşteri, personel, banka, kimlik/vergi no) için açık risk-kabulü ve onay kelimesi
ister. Muğlak ifade ("dene", "çek") yetmez.

### 15.2 Fikri-sermaye ve kimlik sızıntısı koruması

Çekirdek **public**tir; iki yönlü koruma vardır:

- **Core → proje:** metodoloji proje reposuna gönderilemez (dört katman, Bölüm 5.4).
- **Proje → core:** core'a yazılan içerikte ve **dosya adında** kimlik izi taranır. Kapsam:
  isim listesi (müşteri/sistem/kişi; IGNORECASE) + yapısal desenler — makine-lokal kullanıcı
  yolu, e-posta, **gerçek Z-obje adı** (`Z<MOD><NNN>`; kanonik örnek `Z<MOD>000`/`Z<MOD>001`
  muaf), **SAP kullanıcı adı** (`D_XXXX` biçimli placeholder'lar muaf).

> Desenler `genericize_common.py`'de **tek kaynaktan** gelir. İki guard'ın ayrı listelerden
> beslendiği dönemde biri güncellenip diğeri unutuluyordu; bir test artık kopyanın geri
> gelmesini engelliyor.

### 15.3 Donmuş (salt-okunur) yedekler
Arşiv kökler `project.yaml` → `frozen_readonly_paths` ile işaretlenir; bu köklere yazma
reddedilir, okuma serbesttir.

### 15.4 Davranış-yüzeyi güvenlik duvarı
`CLAUDE.md`, `.claude/**`, `.mcp.json`, `project.yaml`, `hook_shim.py` yalnız lider-onaylı PR
ile değişir; oturum-içi değişimi `ConfigChange` hook'u izler; hash envanteri beklenmedik
değişimi yakalar.

### 15.5 Yabancı repoya ilk temas (misafir modu)
Önce yapay-zekâsız ön-tarama, sonra `--safe-mode` oturum, sonra `guest_mode` ile geçici kural
dosyası. Kod-sınıfı (hook/MCP) incelenmeden normal oturum açılmaz.

### 15.6 Denetim izi
Her SAP-yazımı reviewer'dan, her değişiklik PR + CI'dan geçer; git geçmişi + davranış-manifest
+ oturum notları uçtan uca izlenebilirlik sağlar. Yanlış değişiklik `stable`'a döndürülür.

---

## 16. Onboarding: Yeni Geliştirici ve Yeni Proje

### 16.1 Yeni geliştirici
Ayrıntı: `DEV_CORE/ONBOARDING.md`.

```powershell
# 1. Ön-koşullar: git (autocrlf=false, longpaths=true), Node/npm, claude CLI, GitHub kimliği
# 2. Projeyi klonla, sonra:
python core/scripts/team_setup.py       # junction + hooksPath + memory seed + CORE-INDEX
# 3. .conn_adt doldur (şablon: core/claude/conn_adt.template)
# 4. python core/scripts/ix_doctor.py   # kurulumu doğrula
# 5. Son SESSION_NOTES girdisini oku
```

### 16.2 Yeni proje açma
Ayrıntı: `DEV_CORE/PROJECT_BOOTSTRAP.md` (STEP 0–6).

```powershell
gh repo create <ORG>/XYZ --private
git clone https://github.com/<ORG>/XYZ.git C:\IX\XYZ
python C:\IX\DEV_CORE\scripts\init_project.py C:\IX\XYZ --name XYZ --repo-mode full
python C:\IX\DEV_CORE\scripts\team_setup.py --project C:\IX\XYZ
#   project.yaml + .conn_adt doldur
python core/scripts/behavior_manifest.py generate
mkdir <source_root>\SD
python core/scripts/bootstrap_package.py ZSD001_CLC --module SD --title "..." --owner "<OWNER>"
git add -A ; git commit -m "chore(bootstrap): XYZ iskeleti" ; git push -u origin main
python core/scripts/ix_doctor.py
```

`init_project.py` **üretir** (kopyalamaz): `CLAUDE.md` (yasaklar damgalı + `@core` import),
`README.md`, `.claude/settings.json`, `scripts/hook_shim.py`, `scripts/git-hooks/pre-commit`,
`project.yaml`, `.gitignore` (sızıntı kilidi + sırlar + runtime), `.gitattributes`, `.mcp.json`,
`.github/workflows/guard.yml`, `.github/CODEOWNERS` ve boş dizin iskeleti.
`team_setup.py` beş junction'ı kurar, **projede `core.hooksPath`'i kablolar**, memory tohumlar,
`CORE-INDEX`'i üretir.

> **Bu zincirin kendisi test edilir.** 2026-07-10'da `template_project` sıfırdan yeniden
> üretildi; prova yedi bosluk buldu (üç hook şablonda yoktu, `validators` CI job'u şablona
> yansımamıştı, `pre-commit` hiç üretilmiyordu, `.gitignore` ~35 satır geriydi, kök `README`
> yoktu, `CORE-INDEX` yalnız onarım yolunda üretiliyordu, CI ağı `.claude/rules/**`'ı
> aramıyordu). Hepsi kapatıldı ve **C-TPL-01** gate'i tekrarını engelliyor.

**Yeni proje mevcut bir projeye yerinde dönüşüm olarak değil, yeni kök altında sıfırdan
kurulur** (ADR 0020 §5, yan-kurulum): rollback radikal basitleşir, yarı-dönüşmüş ara-durum
riski sıfırlanır.

### 16.3 Kabul gate'i (STEP 6 sonrası)

| # | Kanıt | Nasıl |
|---|---|---|
| 1 | Loader + hook'lar çalışıyor | Oturum aç → ekran-teyidi formatı geliyor |
| 2 | MCP kendi sistemine bağlı | `ping` + read-only `adt_get` |
| 3 | Validator'lar PASS | `run_all_validators.py` |
| 4 | Sızıntı kilidi çalışıyor | `git ls-files core/ .claude/agents .claude/rules` → boş |
| 5 | Kurulum sağlığı | `ix_doctor.py` → FAIL yok |
| 6 | **L1b kuralları gerçekten yükleniyor** | Bir `.abap` okut → `.tmp/instructions-loaded.log`'da `path_glob_match` |

---

## 17. Bilinen Sınırlar ve Açık Kalemler

Dürüstlük, mimarinin bir parçasıdır. Bilinen sınırlar:

| Konu | Durum |
|---|---|
| **L1b yükleme kanıtı** | `claude/rules/` kuruldu ve kablolandı; **gerçekten yüklendiği henüz canlı ölçülmedi** (`InstructionsLoaded` logger'ı sonradan eklendi; hook'lar oturum başında kaydedilir). Taze oturumda `.tmp/instructions-loaded.log`'da `path_glob_match` aranmalıdır. |
| **Kabuk kaçışları** | `pre_tool_guard`, `echo >> core/…` / `cp` / `tee` gibi yolları kapatmaz (bilinçli; telafi pre-commit + CI). |
| **Git geçmişi** | Public core'un HEAD'i kimlik izinden temizlendi; **commit geçmişi temizlenmedi** (ayrı, ağır bir operasyon). |
| **D34d politika tablosu** | Mekanizma canlı; profil-özel `available_on` daraltmaları kanıt bekliyor (ilk `s4_public`/`btp_abap` projesi). |
| **Ruleset onay kaydı** | Tek code-owner'da "1 onay" kuralı fiilen bypass'la geçiliyor (13.2). |
| **Profil matrisi** | Rehberdir, kanıt değildir; her capability iddiası canlı testle doğrulanmalıdır. |

---

## EK-A. Karar Kayıtları (ADR) Dizini

Çekirdek **21** ADR içerir (`DEV_CORE/governance/decisions/`). Numara 0015 proje-seviyesindedir
(çekirdekte yoktur) — iki ADR uzayı aynı numaralandırmayı paylaşır.

| ADR | Konu |
|---|---|
| 0001 | Tek branch (PR-zorunlu modeliyle revize) |
| 0002 | Paket adlandırma |
| 0003 | Katmanlı kural mimarisi (L1–L4) |
| 0004 | Modül-bazlı klasör organizasyonu |
| **0005** | Standart SAP nesne koruması + sistem-state yasakları |
| 0006 | Reviewer (ön-inceleme) ajan deseni |
| 0007 | SAP ADT MCP sunucusu |
| 0008 | Liste ekranı grid (`sap.ui.table`) paritesi |
| 0009 | Ortak value-help CDS politikası |
| 0010 | Katman-bazlı salt-okunur guard (bağlantı tutarlılığı) |
| 0011 | Veri-çıkarma / PII guard (KVKK) |
| 0012 | Klasik ALV template-first |
| 0013 | Kaynak/referans doküman ayrımı (`ref_docs`) |
| 0014 | Belge kilidi (app-level vs draft) |
| 0016 | Source-drift önleme (repo ↔ canlı senkron) |
| 0017 | UI build doğrulama — kanonik desen + tuzak gate |
| 0018 | Agent takım yapısı (katman + bug-gate) |
| **0019** | Kural-enforcement mimarisi (3-eksen coverage) |
| **0020** | Canlı-çekirdek junction mimarisi |
| **0021** | Kesin yasaklar fiziksel damga |
| 0022 | Intake Triage Gate (iş-alım katmanı) |

## EK-B. Terminoloji

- **DEV_CORE:** metodoloji çekirdeği reposu (tek kaynak, public).
- **junction:** Windows dizin bağlantısı; proje `core/` → DEV_CORE.
- **hook:** belirli bir olayda otomatik çalışan script.
- **guard:** araç-öncesi denetim; kural ihlalinde eylemi reddeder (RED, exit 2).
- **validator:** bir kaynağı/kuralı kontrol eden `check_*.py`; PASS/FAIL.
- **gate (kapı):** bir eylemin geçmesi için sağlanması gereken kontrol.
- **reviewer:** SAP-yazımı öncesi ön-inceleme; PASS/WARNING/BLOCKER.
- **ITG:** Intake Triage Gate — geliştirme talebi alım/sınıflama katmanı.
- **profil:** projenin SAP türü (`ecc`/`s4_private`/`s4_public`/`btp_abap`).
- **L1a / L1b / L1c:** her-oturum / glob-tetiklemeli / derin-referans davranış katmanları.
- **fail-closed:** bilgi eksikse yüzeyi kapatma (varsayım yapmama) davranışı.
- **stable etiketi:** çekirdeğin bilinen-iyi git noktası; rollback hedefi.
- **genericize:** core'a girecek içerikten proje/müşteri/sistem/kişi izini temizleme.
