# ix-works Mimarisi — Kurulum ve İşletim Kılavuzu

> **Amaç.** Bu belge, birden çok SAP geliştirme projesini tek bir metodoloji çekirdeği
> üzerinden yürüten "ix-works" mimarisini tanımlar. Hedef okuyucu iki gruptur: mimariyi
> değerlendiren/işleten **yöneticiler** (Bölüm 0–1 ve 15 yeterlidir) ve sistemi kuran/kullanan
> **geliştiriciler** (tüm belge). Belge, sistemin fiili durumunu yansıtır; her yetenek,
> arkasındaki dosya/kural referansıyla birlikte anlatılır.
>
> **Sürüm bilgisi.** Bu belgedeki tüm proje/paket adları örnektir (`<PROJE>`, `<ORG>`,
> `ZSD001_CLC`); gerçek bir kurulumda kendi değerlerinizle değişir. Standart SAP nesneleri
> (VBAK, LIKP, BAPI_*) gerçektir.

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
- [8. Kural Mimarisi (L1-L4) ve SORU 0](#8-kural-mimarisi-l1-l4-ve-soru-0)
- [9. İş-Alım: Intake Triage Gate (ITG)](#9-iş-alım-intake-triage-gate-itg)
- [10. SAP ADT MCP Sunucusu](#10-sap-adt-mcp-sunucusu)
- [11. Kurumsal Hafıza (Memory) Sistemi](#11-kurumsal-hafıza-memory-sistemi)
- [12. Çok-Ajanlı Çalışma Modeli](#12-çok-ajanlı-çalışma-modeli)
- [13. GitHub Mimarisi ve Çalışma Akışı](#13-github-mimarisi-ve-çalışma-akışı)
- [14. Sağlık ve Kalite Araçları](#14-sağlık-ve-kalite-araçları)
- [15. Güvenlik, Gizlilik ve Uyumluluk](#15-güvenlik-gizlilik-ve-uyumluluk)
- [16. Onboarding: Yeni Geliştirici ve Yeni Proje](#16-onboarding-yeni-geliştirici-ve-yeni-proje)
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
   uygulanan" bir şeydir. İnsan disiplinine değil, mimariye dayanır — bu, aynı aracı
   kullanan farklı kişilerin çıktılarındaki kalite farkını azaltır.

2. **Yapay-zekâ ajanı da kurallara tabidir.** Sistem, bir yapay-zekâ ajanı tarafından
   kullanıldığında, ajanın her önemli eylemi (dosya yazma, SAP'ye erişim, komut çalıştırma)
   gerçek zamanlı olarak denetlenir. Standart SAP nesnesine dokunma, donmuş yedeğe yazma
   veya fikri-sermaye sızdırma gibi eylemler eylem anında reddedilir.

3. **Değişiklikler denetlenebilir ve geri alınabilir.** Her değişiklik kısa-ömürlü dal +
   inceleme (PR) + otomatik kontrol (CI) sürecinden geçer. Merkezi çekirdek, bilinen-iyi
   bir noktaya (stable etiketi) tek adımda döndürülebilir.

Model, gerçek kurumsal SAP ortamları için tasarlanmıştır: Windows üzerinde çalışır,
şirket-içi (on-prem) SAP sistemlerine VPN üzerinden bağlanır, birden çok sistem katmanını
(geliştirme/kalite/üretim) ayrı yönetir ve KVKK/veri-gizliliği kısıtlarını gözetir.

---

## 1. Mimari Felsefe: Canlı Çekirdek + Junction

### 1.1 Çözülen sorun
Birden çok proje aynı metodolojiyi (standartlar, hook'lar, validator'lar, şablonlar)
kullandığında, klasik yaklaşım her projeye bir kopya koymaktır. Kopyalar zamanla birbirinden
uzaklaşır (drift); bir düzeltme/ders bir projede yapılır, diğerlerine taşınmaz; hangi
kopyanın güncel olduğu belirsizleşir. Proje sayısı arttıkça bu bakım yükü katlanır.

### 1.2 Çözüm — tek canlı kaynak
ix-works, metodolojinin tamamını `DEV_CORE` adında **tek bir repoda** tutar ve her projeye
Windows **junction** (dizin bağlantısı) ile bağlar. Proje klasörü içindeki `core/` girişi,
fiziksel olarak DEV_CORE'un çalışan kopyasını gösterir. Böylece:

- Metodoloji **bir yerde** yaşar; tüm projeler onu **anlık** görür.
- Bir kural/ders bir kez yazılır (`DEV_CORE`), junction'la her projeye ulaşır.
- Kopya-drift yapısal olarak imkânsızdır — kopya yoktur.

Karar kaydı: **ADR 0020** (Canlı-Çekirdek Junction Mimarisi).

### 1.3 Neden junction (ve neden diğerleri değil)
| Alternatif | Neden seçilmedi |
|---|---|
| Her projeye kopya | Drift + N-kat bakım (çözülen sorunun kendisi) |
| Git submodule | Sürüm-sabitleme "canlı"lığı bozar; her projede ayrı pin/pull yükü |
| Git subtree | Geçmiş şişer; senkron karmaşık |
| Kullanıcı-seviyesi paylaşım (`~/.claude`) | Git-dışı (ekibe akmaz); kapsam taşması (alakasız projeye kural) |
| Tek monorepo | Projeler ayrı yaşam-döngüsü/izin/repo ister |

Junction, "canlı tek kaynak" ile "projelerin bağımsız git repoları" gereksinimlerini aynı
anda karşılayan tek seçenektir. DEV_CORE ile projeler arasında **git bağı yoktur**; her biri
kendi GitHub reposudur, yalnız dosya-sistemi düzeyinde bağlıdır.

### 1.4 Metodoloji vs proje ayrımı (SORU 0)
Yeni bir bilgi üretildiğinde tek bir soru sorulur: *"Bu metodoloji mi, projeye mi özel?"*
Metodoloji-nitelikli her şey (pattern, validator, standart, ders) `DEV_CORE`'a; projeye-özel
her şey (iş kuralı, paket, müşteri süreci) proje reposuna gider. Bu ayrım, çekirdeğin jenerik
(kopyalanabilir/şablonlanabilir) kalmasını, proje reposunun ise iş-bilgisini taşımasını sağlar.
(Ayrıntılı karar ağacı: Bölüm 8.)

---

## 2. Temel Yetenekler ve Tasarım Kararları

Bu bölüm, sistemin ayırt edici davranışlarını olgu düzeyinde listeler. Her madde, ilgili
bölüme referans verir.

**1. Kendi kendini denetleyen kalite altyapısı.**
`ix_doctor` adlı 7 katmanlı bir sağlık-kontrol aracı, kurulumun bütünlüğünü (junction,
git, GitHub kuralları, hook drift'i, MCP bağlantısı, validator geçişi) doğrular. Ek olarak
guard katmanları dönemsel olarak **bozuk girdiyle** sınanır; bu, bir kuralın "tanımlı
olması" ile "fiilen çalışması"nı ayrı ayrı doğrular. (Bölüm 14)

**2. Yapay-zekâ ajanı için davranış denetimi.**
Ajanın her eylemi, işletim öncesinde bir denetim katmanından (`pre_tool_guard`) geçer.
Standart SAP nesnesine yazma, transport/paket yaratma, donmuş yedeğe yazma, çekirdek
içeriğini proje reposuna gönderme gibi eylemler eylem anında reddedilir. Temel yasaklar,
projenin kök yapılandırma dosyasına fiziksel olarak damgalanmıştır; bağlantı kopsa bile
bu kurallar yüklüdür. (Bölüm 6)

**3. Her kural bir kapıyla zorlanır.**
"Gate'siz kural, kuralsızdır" ilkesi (ADR 0019): her kalite kuralının arkasında onu
otomatik uygulayan bir script/hook/checklist bulunur ve bir kapsam-denetleyici (`check_rule_gate_coverage`)
bu bağın var olduğunu doğrular. Kural belgede kalıp uygulanmadan geçemez. (Bölüm 7)

**4. Yaz-bir-kez, devral-her-yerde.**
Metodoloji tek merkezde; tüm projeler junction'la güncel. Yeni proje kurulduğunda çekirdeği
sıfır-eforla devralır; mevcut projeler anlık görür. (Bölüm 1, 4)

**5. Biriken kurumsal hafıza.**
Karşılaşılan her hata, tekrarını önlemek üzere kalıcı hafızaya (memory + lessons-learned)
işlenir. İş geldiğinde "benzerini daha önce yaptık mı?" araması yapılır. Bilgi kişilerde
değil, sistemde birikir. (Bölüm 11)

**6. Kanıta dayalı çalışma ("tahmin yasak").**
Ajan, bir iddiayı doğrulamadan aksiyona geçemez; hatırlanan bilgi hipotez, canlı sistem
otoritedir (ADR 0016). Bu, yanlış varsayımdan doğan hataları (ör. değişmiş bir nesneyi
eski haliyle varsayma) azaltır. (Bölüm 6, 9)

**7. İşe-orantılı alım süreci (ITG).**
Bir geliştirme talebi geldiğinde sistem, işin kapsamını (küçük düzeltme / lokalize /
kapsamlı) sınıflar, ilgili fonksiyonel modülün kontrol-listesini yükler, isterlerden
araştırılması gereken konuları çıkarır ve üç eksende (alan bilgisi + canlı sistem +
kurumsal hafıza) araştırma yapar. Küçük işe ağır süreç binmez; kapsamlı işe disiplin atlanmaz. (Bölüm 9)

**8. Uçtan uca denetlenebilirlik.**
Her SAP-yazımı bir ön-inceleme (reviewer) kapısından, her değişiklik PR+CI+davranış-manifest'ten
geçer. Merkez, bilinen-iyi noktaya geri döndürülebilir. (Bölüm 15)

**9. Çok-katmanlı SAP hedefi.**
Aynı çekirdek dört SAP profilini (ECC, S/4 private, S/4 public, BTP ABAP) destekler; her
projenin `project.yaml`'ındaki profil, hangi kuralların geçerli olduğunu belirler. (Bölüm 4)

**10. Gerçek kurumsal ortam desteği.**
Windows junction, VPN-kopukluğu izleyen bir arka-plan bekçisi (watchdog), çoklu sistem-katmanı
(DEV/QA/PRD) ve Windows'a özgü kodlama tuzaklarının çözümü — laboratuvar değil, saha kullanımı
için tasarlanmıştır.

---

Aşağıdaki üç bölüm (3–5) iki fiziksel katmanın anatomisini ve ikisini birbirine bağlayan
junction mekanizmasını tanımlar: (1) metodolojinin tek kopyası olan **DEV_CORE** reposu ve
(2) her SAP projesi klasörü.

## 3. DEV_CORE Anatomisi

DEV_CORE, metodolojinin (standartlar, playbook, script/validator/hook, MCP server, agent
ve skill tanımları) tek fiziksel kopyasının tutulduğu git reposudur. Projeler bu içeriği
kopyalamaz; junction ile canlı olarak okur (bkz. Bölüm 5). Her düzeltme bir kez burada yazılır,
junction'lı tüm projeler aynı anda görür.

### Kök seviyesi dosyalar

| Dosya | İçerik / işlev |
|---|---|
| `CLAUDE.core.md` | Çekirdek loader. Proje `CLAUDE.md`'si `@core/CLAUDE.core.md` ile bunu yükler. Katman özeti (L1–L4), SAP profil modeli, 4-adım session protokolü, T1–T11 tetikleyiciler + SORU 0, kod gate'leri tablosu, dosya indeksi. Metodoloji buradadır; proje-özel bilgi burada tutulmaz. |
| `AGENTS.md` | L1 katmanı: agent davranış kuralları — git iş akışı, ADT işlem sırası, project skill kullanımı. |
| `README.md` | Reponun ne olduğu ve nasıl clone edildiğine dair giriş. |
| `MAINTENANCE.md` | Canlı-çekirdek işletim el kitabı: PR/CI akışı, `stable` tag ile rollback, `project.yaml` anahtar kataloğu, sürüm politikası. ADR 0020 "neden"i, bu dosya "nasıl"ı anlatır. |
| `ONBOARDING.md` | Yeni/güncellenen geliştiriciyi ortamla senkron etme adımları (`onboard` komutunun düz-metin karşılığı). |
| `PROJECT_BOOTSTRAP.md` | Yeni proje açılış prosedürü (init_project → team_setup → paket bootstrap sıralaması). |
| `.gitignore` / `.gitattributes` / `.github/` | Repo hijyeni: ignore kuralları, CRLF/satır-sonu politikası, CI workflow tanımları. |

### Dizinler

```text
DEV_CORE/
├── claude/          Claude Code varlıkları (agent, skill, command, template, memory-seed)
├── scripts/         Python araçları — hooks/ + validators/ + tekil araçlar + utils/
├── mcp_servers/     SAP ADT MCP server (typed tool katmanı + guardrail'ler)
├── standards/       L2 — stabil kurumsal/proje standartları (01–09)
├── playbook/        L3 — operasyonel ADT pattern bankası + checklists/ + modules/
├── profiles/        SAP profil yetenek matrisleri (4 yaml)
├── governance/      ADR'ler + işletim modeli + tooling envanteri
├── templates/       Yeni-paket iskelet şablonları
└── intake/          Dış içerik karantina/gümrük alanı
```

#### `claude/` — Claude Code varlıkları

Plugin-şekilli varlıkların tek çatı altında gruplandığı dizin. Proje `.claude/` altındaki
üç junction (agents, skills, commands) buraya bakar.

| Yol | İçerik |
|---|---|
| `agents/` | 6 rol tanımı (`.md`, YAML frontmatter'lı). Rol modeli tek-yazıcı (single-writer) serileştirmesine dayanır — aşağıda ayrı tablo. |
| `skills/` | Project skill'leri: `sap-abap-dev` (SAP/ABAP/RAP/CDS/DDIC iş yönlendirmesi + ADR 0005 yasakları), `playwright-cli` (tarayıcı otomasyonu). |
| `commands/` | Slash-komutlar. `onboard` — geliştirici senkron akışı. |
| `memory-seed/` | Yeni proje memory'sinin tohumlandığı `MEMORY.md` indeksi + `feedback_*.md` ders dosyaları (`seed_memory.py` ile kopyalanır). |
| `CLAUDE.project.template.md` | Yeni proje ince `CLAUDE.md`'sinin şablonu (init_project doldurur). |
| `settings.template.json` | Proje `.claude/settings.json`'ının şablonu — hook zinciri `hook_shim.py` üzerinden bağlanır. |
| `hook_shim.template.py` | Proje-lokal hook yönlendiricisinin şablonu (D15; Bölüm 5'te ayrıntılı). |
| `kesin-yasaklar.canonical.md` | KESİN YASAKLAR'ın kanonik metni. Her projenin kök `CLAUDE.md`'sine fiziksel damgalanır; `sync_yasaklar.py` kanonik değişince yeniden damgalar, `check_kesin_yasaklar.py` damga eşliğini zorlar (ADR 0021). |
| `managed-policy.template.json` | Yönetilen izin politikası şablonu. |
| `conn_adt.template` | SAP bağlantı dosyasının (`.conn_adt`) şablonu. |

**Agent rolleri (6):** tek SAP-yazıcısı ilkesine (single-writer) göre ayrılmıştır. Yazma
yetkisi tek rolde toplanır; diğerleri tasarlar, yerel kaynak hazırlar, read-only SAP
analizi yapar.

| Rol | Yetki sınırı |
|---|---|
| `adt-gateway` | SAP'ye yazabilen **tek** rol. Tüm create/push/activate/delete/DDIC/post_shell işlemleri buradan geçer (serileştirme). run_review pre-flight + ADR 0005/0006/0007 guardrail'leri. |
| `backend-expert` | ABAP/RAP/CDS/DDIC/class. Tasarım + yerel kaynak + read-only analiz. SAP-yazma tool'u yok. |
| `frontend-expert` | Freestyle UI5 + OData V2. Yerel UI kaynağı (controller/view/i18n/manifest) + read-only. SAP-yazma tool'u yok. |
| `bug-expert` | Adversarial inceleme (read-only). Değişimi/dokümanı checklist'e karşı çürütmeye çalışır; verdict PASS/WARNING/BLOCKER. Yazmaz. |
| `sap-feature` | Modül/uygulama sahibi — uçtan uca tasarım + yerel kaynak, read-only. SAP-yazma tool'u yok. |
| `sap-research` | Salt-okunur keşif/analiz + web araştırması. Yalnız `.tmp/` rapor yazar. |

#### `scripts/` — Python araçları

Üç kategoriye ayrılır: olay-tetikli hook'lar, deterministik validator'lar ve tekil
araçlar.

**`scripts/hooks/` (olay-tetikli, `hook_shim.py` üzerinden çağrılır):**

| Hook | İşlev |
|---|---|
| `session_start.py` | Oturum başı: junction sağlığı, davranış-manifest diff, "origin gerisinde" uyarısı, junction onarım önerisi. |
| `pre_tool_guard.py` | Tool öncesi guard: donmuş/salt-okunur yollara yazma reddi, junction hedefine özyinelemeli-silme bloğu, SAP-yazma öncesi yasak/bağlantı-tutarlılık kontrolü. |
| `pull_before_edit.py` | SAP source düzenleme öncesi tazelik backstop'u (ADR 0016). |
| `post_validate.py` / `post_tool_failure.py` | Tool sonrası doğrulama / başarısızlık işleme. |
| `config_change_guard.py` | Davranış-yüzeyi (settings/manifest) değişimi seans-içi yakalama. |
| `skill_injector.py` | İş türüne göre ilgili skill'i devreye alma (profil-okuyan). |
| `intake_triage.py` | Dış-içerik ilk temas triyajı (ADR 0022). |
| `tooling_radar_check.py` | Kurulu tooling/plugin envanter kontrolü. |
| `pre_compact.py` | Context compact öncesi checkpoint. |
| `watchdog_*` | Background agent stall izleme (heartbeat/daemon). |
| `README.md` | Hook bakım karar ağacı (T11): validator mı, checklist mi, hook mu, pre_tool_guard mı. |

**`scripts/validators/` (deterministik kural kontrolleri, ~36 adet):** Tek komut
`run_all_validators.py` ile core + proje `validators-local/` birlikte, profil-modlu koşar.
Örnek kapsamlar: `check_kesin_yasaklar` (damga eşliği), `check_core_not_committed`
(fikri-sermaye sızıntı kilidi), `check_sap_master_language` (Z obje TR label),
`check_object_in_correct_pkg` (paket sınırı), `check_list_view_grid` (grid liste
standardı), `check_ui5_freestyle_traps` (FE tuzakları), `check_released_objects` (clean
core), `check_rule_gate_coverage` (her kuralın gate'lenmiş olması). `run_review.py` SAP
yazma öncesi reviewer pre-flight'ı (ADR 0006).

**Tekil araçlar (seçme):**

| Araç | İşlev |
|---|---|
| `init_project.py` | Yeni proje iskeletini template'lerden **üretir** (kopyalamaz). |
| `team_setup.py` | Geliştirici/proje kurulumu + junction kur/onar (`--repair-junctions`, `--provision-worktree`). |
| `bootstrap_package.py` | Yeni SAP paketi iskeleti (`.rules.md` + docs + SESSION_NOTES). |
| `sync_yasaklar.py` | KESİN YASAKLAR kanonik → tüm projeleri yeniden damgalama. |
| `ix_doctor.py` / `sap_doctor.py` | Ortam / SAP bağlantı sağlık teşhisi. |
| `deploy_ui.py` | Freestyle UI kanonik non-interaktif deploy (build + deploy + canlı-hash doğrulama). |
| `behavior_manifest.py` | Davranış-yüzeyi manifest üretimi/diff. |
| `statusline.py` | Claude Code status line üreteci. |
| `seed_memory.py` / `setup_plugins.py` | Memory tohumlama / plugin kurulumu (onboarding). |
| `switch_tier.py` | Çoklu-tier SAP bağlantı değişimi (ADR 0010). |
| `sap_sync_pull.py` / `source_drift.py` | Canlı-repo senkron / drift tespiti (ADR 0016). |
| `utils/project_config.py` | Proje kökü + `project.yaml` okuma tek kaynağı (junction `resolve()` tuzağına karşı; D24). |

#### `mcp_servers/sap_adt/` — SAP ADT MCP server

`sap_adt_lib.py` üzerine typed tool katmanı (ADR 0007). Tekil obje işlemleri (create,
activate, push, search, lock, table-read) MCP tool'u; CSV-batch/validator/gate işi
script. Server-side guardrail: ADR 0005 hardcoded (Z/Y prefix zorunlu, TR text zorunlu,
standart obje değişimi yok, transport release yok) + profil-bazlı tool-blok + bağlantı
tutarsızlık gate'i. Bileşenler: `server.py`, `guardrails.py`, `data_guard.py`,
`_reviewer.py`, `_conn.py`, `tools/`, `tests/`. (Ayrıntı: Bölüm 10.)

#### `standards/` — L2 stabil standartlar

Değişim sıklığı düşük, `applies_to:` frontmatter'lı kurallar. `01-naming` (paket/WRICEF/
namespace), `02-coding-backend` (klasik SEGW/OData v2), `03-coding-ui-fiori`,
`04-documentation-fs-ts`, `05-coding-rap`, `06-coding-classic-dialog`, `07-output-forms`,
`08-classic-gui-f1-help`, `09-packing-instruction-consumption`, `README.md` (indeks).

#### `playbook/` — L3 operasyonel pattern bankası

Deneme-yanılma ile bulunmuş çalışan ADT pattern'leri, denenen başarısız yollar,
gotcha'lar. Obje tipine göre bölünmüştür: `adt-foundation` (temel ADT işlemleri),
`adt-tables-structures`, `adt-domain-dtel`, `adt-cds`, `adt-rap`, `adt-classes`,
`adt-programs`, `adt-fugr-functions`, `adt-lock-objects`, `adt-message-class`, `adt-mcp`,
`ui-freestyle-odata-v2`, `ui-backend-rap`, `coding-patterns`, `odata-services`,
`known-errors`, `lessons-learned` (cross-cutting hata pattern + trigger phrase), `howto-*`
(dynpro/gui-status, document-lock, packing, KD-PDF). Alt dizinler: `checklists/` (15 iş
türü kontrol listesi — cds/rap/struct/domain-dtel/table-update/ui-*/adobe-forms/doc/itg),
`templates/` (kanonik kod şablonları, ör. klasik ALV), `modules/` (modül-özel bilgi, ör.
`sd.md`).

#### `profiles/` — SAP profil yetenek matrisleri

Her `.yaml` bir SAP profilini tanımlar: `ecc`, `s4_private`, `s4_public`, `btp_abap`.
İçerik yapısı (`s4_private.yaml` örneği): `capabilities` (rap/abap_cloud/classic_dynpro/
cds/amdp/segw_odata/transport… her biri `preferred|available|allowed|forbidden`),
`release_overrides` (S/4 release'e göre farklar), `policy_axis` (`cleancore_policy` =
strict|balanced|classic → hangi yetenek kısıtlanır), `data_sources` (released-obje/clean-
core sınıflandırma otoriter kaynakları). Matris rehberdir, kanıt değildir: capability
iddiası canlı testle doğrulanır. Bir projenin hangi kuralın aktif olduğu bu profil +
`project.yaml` birleşiminden çözülür (Bölüm 5).

#### `governance/` — kararlar ve işletim

| İçerik | Açıklama |
|---|---|
| `decisions/` | ADR'ler (0001–0022). Metodoloji-seviyesi mimari kararlar; ör. 0003 (L1–L4 katman), 0005 (SAP standart-obje koruma + yasaklar), 0007 (MCP server), 0018 (agent takım yapısı), 0020 (junction mimarisi), 0021 (yasaklar fiziksel damga). |
| `agent-teams-operating-model.md` | Takım işletim modeli: dosya bölgeleri (Zone A/B/C), yazım yetkisi, gün-sonu/resume disiplini. |
| `tooling-plugins.md` / `tooling-radar.md` | Kurulu plugin envanteri / tooling değişim radarı. |
| `vscode-setup.md` | Editör kurulum notları. |

#### `templates/` — yeni-paket iskeleti

`new-package/` altında `.tmpl` şablonlar: `README.md.tmpl`, `SPEC.md.tmpl`,
`SESSION_NOTES.md.tmpl`, `folders.txt` (paket dizin ağacı), `ref_docs/`. `bootstrap_package.py`
bunlardan üretir.

#### `intake/` — dış içerik gümrüğü

Dışarıdan gelen her metodoloji parçası (skill/hook/script/agent/playbook) core'un canlı
yüzeyine doğrudan girmez; önce buraya iner, güvenlik+lisans+genericize incelemesinden
geçer, sonra PR ile hedefe taşınır (F4 firewall, ADR 0022). Sebep: core canlıdır — buraya
giren şey junction'lı tüm projelerde anında etkilidir.

---

## 4. Proje Klasörü Anatomisi

Bir proje klasörü üç tür içerikten oluşur: (a) core'a bakan junction'lar, (b) proje-lokal
davranış/config dosyaları, (c) proje-özel iş içeriği (SAP kaynağı, bağlantı, governance).
Metodoloji fiziksel olarak burada **yoktur** — junction üzerinden okunur.

```text
<PROJE>/
├── core/  ═══════════════════► DEV_CORE            (junction)
├── .claude/
│   ├── agents/  ═════════════► DEV_CORE/claude/agents    (junction)
│   ├── skills/  ═════════════► DEV_CORE/claude/skills     (junction)
│   ├── commands/ ════════════► DEV_CORE/claude/commands   (junction)
│   ├── settings.json            (proje-lokal, commit'li — hook zinciri)
│   ├── settings.local.json      (kişisel, gitignore)
│   ├── behavior-manifest.json   (davranış-yüzeyi manifest, proje-lokal runtime)
│   ├── active_package           (aktif paket işareti, gitignore)
│   └── .current_session / .mcp_active_system / .statusline_vpn_cache  (runtime state)
├── CLAUDE.md                    (ince loader — yasaklar damgalı + @core import + proje-özel)
├── project.yaml                 (proje kimliği: profil, source_root, gate config'leri)
├── .conn_adt                    (SAP bağlantı — gitignore)
├── conn/                        (çoklu-tier .env'ler — *.env gitignore, template'ler commit'li)
├── .mcp.json                    (MCP server tanımı — core'dan yüklenir, env-first)
├── .gitignore / .gitattributes  (SIZINTI KİLİDİ + CRLF politikası)
├── scripts/
│   ├── hook_shim.py             (proje-lokal hook yönlendiricisi — commit'li)
│   ├── validators-local/        (proje-özel validator'lar)
│   └── workflows/ TempScripts/  (proje iş scriptleri / geçici)
├── SOURCE_CODES/                (SAP kaynak kodu — modül-bazlı; ad project.yaml'dan)
│   └── <MODULE>/<PKG>/           (ör. SD/ZSD001_CLC/ — cds classes functions docs ui .rules.md)
├── governance/                  (proje: ADR'ler, deferred-triggers, package-registry, RESUME)
├── playbook-local/ standards-local/   (proje-özel overlay — core mekanizması otokeşif)
└── .tmp/                        (scratch/çıktı — gitignore)
```

### Core'dan gelen vs Proje-özel — net ayrım

| Dosya / dizin | Kaynak | Not |
|---|---|---|
| `core/` | **Junction → DEV_CORE** | Tüm metodoloji. Proje reposuna commit'lenmez (`/core/` gitignore'da). |
| `.claude/agents/` | **Junction → DEV_CORE/claude/agents** | 6 rol tanımı. gitignore'da. |
| `.claude/skills/` | **Junction → DEV_CORE/claude/skills** | Project skill'leri. gitignore'da. |
| `.claude/commands/` | **Junction → DEV_CORE/claude/commands** | Slash-komutlar. gitignore'da. |
| `.claude/memory-seed/` | (junction'lanan içerik) | gitignore'da (sızıntı kilidi). |
| `CLAUDE.md` | **Proje-lokal (commit'li)** | Template'ten üretilir. Yasaklar fiziksel damga + `@core/CLAUDE.core.md` import + yalnız proje-özel bölüm. Metodoloji yazılmaz (SORU 0). |
| `.claude/settings.json` | **Proje-lokal (commit'li)** | Template'ten üretilir; hook'lar `hook_shim.py` üzerinden core'a bağlanır. |
| `scripts/hook_shim.py` | **Proje-lokal (commit'li)** | Bilinçli mini-kopya (D15). Junction koptuğunda net hata + onarım komutu; sağlamsa core hook'unu aynı süreçte koşar. |
| `project.yaml` | **Proje-lokal (commit'li)** | Mekanizma/değer ayrımının değer tarafı: profil, release, source_root, prefix'ler, gate config'leri. Core hiçbir değeri hard-code etmez. |
| `.conn_adt` / `conn/*.env` | **Proje-lokal (gitignore)** | SAP bağlantı kimliği/şifre. Yalnız `*.template` + `conn/README.md` commit'li. |
| `.mcp.json` | **Proje-lokal (commit'li)** | MCP server core'dan yüklenir; bağlantı projeden (env-first). |
| `behavior-manifest.json` | **Proje-lokal (gitignore runtime)** | Davranış-yüzeyi sapma tespiti (F2). |
| `active_package` / `.current_session` / `.mcp_active_system` | **Proje-lokal (gitignore)** | Runtime state, paylaşılmaz. |
| `SOURCE_CODES/<MODULE>/<PKG>/` | **Proje-özel (commit'li)** | SAP kaynağı, docs (FS/TS), `.rules.md` (L4 paket kuralı), SESSION_NOTES. |
| `governance/` (proje) | **Proje-özel (commit'li)** | Proje ADR'leri (`<PROJE>-NNN`), deferred-triggers, package-registry, `*-RESUME.md` çapa dosyaları. |
| `playbook-local/` `standards-local/` `validators-local/` | **Proje-özel (commit'li)** | Overlay: core mekanizmaları otomatik keşfeder ve core kurallarıyla birlikte koşar. |
| `.gitignore` / `.gitattributes` | **Proje-lokal (commit'li)** | SIZINTI KİLİDİ satırları + CRLF politikası. |

**Ayrımın özü:** davranış taşıyan her şey ya core'dan junction'la gelir (tek kaynak,
PR+CI'lı) ya da davranış-manifest'te kayıtlıdır. Proje reposu yalnızca proje-özel iş
içeriğini + ince config/loader dosyalarını taşır; metodolojinin kopyası asla girmez.

---

## 5. Çoklu-Proje Flow & Junction Mimarisi

### 5.1 Junction nasıl kurulur ve çalışır

Junction, Windows NTFS'in dizin bağlama mekanizmasıdır (`mklink /J`). Admin/dev-mode
gerektirmez, cross-volume çalışır. Proje klasöründeki dört yol DEV_CORE'a bağlanır:

```text
<PROJE>\core             ──► DEV_CORE
<PROJE>\.claude\agents   ──► DEV_CORE\claude\agents
<PROJE>\.claude\skills   ──► DEV_CORE\claude\skills
<PROJE>\.claude\commands ──► DEV_CORE\claude\commands
```

Kurulumu `team_setup.py` yapar: Python ≥3.10 + MCP requirements kurulumu, DEV_CORE
clone'unda `core.hooksPath scripts/git-hooks` ayarı (pre-commit gate'leri), projede dört
junction kur/doğrula (tek tek rapor), eksik proje-lokal dosyaları template'ten tamamla,
plugin + memory seed, smoke test (statusline + MCP import). Junction kopmuşsa
`team_setup.py --repair-junctions` yalnız onarımı koşar.

Çünkü junction canlı bir bağdır (kopya değil), DEV_CORE working tree'sindeki her değişiklik
tüm projelerde anında görünür. Sürüm sabitleme yoktur — canlılık ilkesi pinning'le
çelişir. Rollback ihtiyacı `stable` tag ile karşılanır: GATE-geçen commit'lerde hareketli
`stable` tag ilerler; core kırılırsa `git checkout stable` deterministik bilinen-iyiye
döndürür.

### 5.2 Çağrı zinciri: proje → DEV_CORE

Hook zinciri, junction koptuğunda guardrail'lerin sessizce kaybolmaması için bir
proje-lokal shim üzerinden geçer:

```text
.claude/settings.json
   └─ hook komutu: python ${CLAUDE_PROJECT_DIR}/scripts/hook_shim.py <hook_adi>
        └─ hook_shim.py (proje repo'da commit'li, ~10 satır)
             ├─ core/ junction sağlam mı?  ── HAYIR ─► NET hata + onarım komutu bas, dur
             └─ EVET ─► core/scripts/hooks/<hook_adi>.py  (runpy — aynı süreç, +0 ms)
```

Shim bilinçli bir mini kopya-artefaktıdır: settings.json doğrudan `core/`'a işaret
etseydi, junction koptuğunda kontrolü yapacak kod da kopuk junction'ın arkasında kalırdı
ve kullanıcı yalnız kriptik "hook command failed" görürdü. Shim proje reposunda
yaşadığından junction'ı bulamazsa net hata + onarım komutu basar; bulursa gerçek core
hook'unu aynı süreçte (`runpy`) koşar (subprocess başına ölçülmüş +86 ms maliyetten
kaçınır). Shim'in core kanoniğiyle drift'i `session_start` hook'unda tam-dosya SHA256 ile
denetlenir.

**Junction `resolve()` tuzağı (D24):** junction üzerinden koşan core script'inde
`Path(__file__).resolve()` fiziksel CORE reposuna çözülür → proje-artefaktı (`.conn_adt`,
`SOURCE_CODES/`…) yanlış kökte aranır. Kural: proje kökü için tek kaynak
`utils/project_config.project_root()` (env `CLAUDE_PROJECT_DIR` → cwd fallback); `__file__`
yalnız core-içi varlıklar için meşru.

### 5.3 project.yaml profil sistemi — hangi kural aktif

Mekanizma core'da, değer projededir. Core script/validator/hook'ları proje davranışını
`project.yaml`'dan okur; hiçbir değeri hard-code etmez. Profil çözümü iki girdiden çıkar:

```text
project.yaml
   sap_profile: s4_private   ──► profiles/s4_private.yaml  (yetenek matrisi)
   release: "2025"           ──► release_overrides["2025"]  (release farkları)
   cleancore_policy: balanced ─► policy_axis["balanced"]    (politika kısıtı)
   master_language: TR       ──► ADR 0005-D uygulaması (Z obje TR login + 4 TR label)
   source_root: SOURCE_CODES ──► kaynak-kod klasörü adı (paket validator'ları buradan okur)
   sql_view_prefix / cds_*   ──► CDS namespace gate'leri
   package_exceptions        ──► paket-sınır istisnaları (check_object_in_correct_pkg)
```

Bir capability (ör. `classic_dynpro`) profil matrisinde `allowed` iken proje
`cleancore_policy: strict` ise `policy_axis.strict` onu `forbidden_by_policy` yapar.
Validator'lar, skill-injector ve MCP guardrail'i profili okur; profil-dışı kural o projede
uygulanmaz. Profil alanları boşsa varsayım yapılmaz — kullanıcı setup'a yönlendirilir,
tool-yüzeyi kesilir. Matris rehberdir, kanıt değildir: capability iddiası canlı testle
doğrulanır.

### 5.4 Sızıntı koruması

Metodoloji (fikri sermaye) müşteri-proje reposuna asla sızmamalıdır. İki katmanlı önlem:

- **`.gitignore` SIZINTI KİLİDİ:** `/core/`, `.claude/agents/`, `.claude/skills/`,
  `.claude/commands/`, `.claude/memory-seed/`, `.claude/behavior-manifest.json` junction
  hedefleri ve runtime state ignore'lanır. Core içeriği git'e hiç girmez.
- **`check_core_not_committed` validator + `pre_tool_guard` commit-kapsam kontrolü +
  proje-repo CI kilidi:** kazara stage'lenen core içeriğini üç noktada yakalar (R1
  sızıntı gate'i).

`resolve()` tuzağının yan etkisiyle ilişkili bir görünürlük kuralı (D29): Grep aracı
`.gitignore`'a uyduğundan proje kökünden yapılan aramalar ignore'lu `core/`'u sessizce
atlar. Metodoloji araması daima `path=core/` ile yapılır; kökten sıfır-sonuç "core'da
yok" anlamına gelmez.

### 5.5 Yeni proje kurulumu adımları

```text
1. init_project.py C:\...\<PROJE> [--name <AD>] [--source-root SOURCE_CODES]
     → template'lerden ÜRETİR (kopyalamaz):
       CLAUDE.md (yasaklar damgalı + @core import), .claude/settings.json,
       scripts/hook_shim.py, project.yaml (profil iskeleti), .gitignore (sızıntı kilidi),
       .gitattributes, .mcp.json, boş: <source_root>/ conn/ playbook-local/
       standards-local/ scripts/validators-local/
2. team_setup.py  (cwd = proje veya --project <PROJE>)
     → Python/pip, DEV_CORE hooksPath, 4 junction kur/doğrula, eksik lokal dosyaları
       template'ten tamamla, plugin + memory seed, smoke test
3. project.yaml doldur   (sap_profile / release / cleancore_policy / master_language /
                          source_root + gate config'leri)
4. .conn_adt + conn/*.env  (SAP bağlantı — gitignore'lu, elle/güvenli girilir)
5. bootstrap_package.py <PKG_FULL> --title "..."   (ilk SAP paketi iskeleti + .rules.md)
```

Yeni proje, mevcut bir projeye **yerinde dönüşüm olarak değil, yeni kök altında sıfırdan**
kurulur (ADR 0020 §5, YAN-KURULUM modeli): rollback radikal basitleşir (en kötü senaryoda
yeni kök komple silinir), yarı-dönüşmüş ara-durum riski sıfırlanır. Worktree'lerde
junction'lar ve gitignore'lu runtime dosyaları kendiliğinden yoktur;
`team_setup.py --provision-worktree` bunları kurar, junction'sız worktree'de oturum
açılmaz (R4 önlemi).

---

Aşağıdaki dört bölüm (6–9), bir projede AI ajanın davranışını **harness seviyesinde**
(hook + validator + kural katmanları) nasıl zorladığını anlatır. Tüm yollar proje kökünden
görecelidir; `core/` bir junction'dır ve gerçek dosyalar DEV_CORE deposundadır.

## 6. Enforcement Katmanı — Ne, Ne Zaman Tetiklenir

Ajan davranışı sohbet metniyle değil, `<PROJE>/.claude/settings.json` içinde
tanımlı **hook zinciriyle** zorlanır. Her hook proje-lokal `scripts/hook_shim.py`
üzerinden çağrılır (junction kopuksa net hata verir); shim, olay adına göre
`core/scripts/hooks/*.py` içindeki gerçek uygulamaya yönlenir. Hook'lar üç sonuç
üretir: **exit 0** (sessiz geç), **stderr + exit 2** (bloklar veya Claude'a geri
besler), veya **`additionalContext` JSON** (prompta bağlam enjekte eder).

### Event → Hook Tetikleme Haritası

| Event | Hook | Ne yapar | RED (exit 2) verir mi |
|---|---|---|---|
| SessionStart | `session_start` | Yasak özeti + oturum protokolü enjekte; junction/drift/manifest/damga sağlık kontrolü | Hayır (bağlam enjekte; ⛔ uyarıları metinle iletir) |
| SessionStart | `tooling_radar_check` | `governance/tooling-radar.md` bayatsa 1-satır nudge | Hayır (nudge) |
| UserPromptSubmit | `skill_injector` | SAP/tarayıcı/yapısal-arama sinyali → iş-türüne özel checklist adını enjekte | Hayır (bağlam enjekte) |
| UserPromptSubmit | `intake_triage` | Geliştirme-talebi sinyali → ITG protokolünü enjekte (ADR 0022) | Hayır (protokol enjekte) |
| PreToolUse `Bash\|mcp__sap-adt__*` | `pre_tool_guard` | 12 RED-katman: yasak-damga, bağlantı, freeze, silme, sızıntı, tehlike, inline-akt, fiori, npm | **Evet** |
| PreToolUse `Edit\|Write\|MultiEdit` | `pre_tool_guard` | Freeze-guard + core-leak + applies_to + silme/sızıntı taraması | **Evet** |
| PreToolUse `Edit\|Write\|MultiEdit` | `pull_before_edit` | Yönetilen SAP source bu seansta çekilmediyse edit'i blokla (ADR 0016) | **Evet** |
| PreToolUse `Agent` | `watchdog_launch` | Arka-plan ajan spawn'unda detached watchdog daemon başlat | Hayır (bağlam enjekte) |
| PostToolUse `Edit\|Write\|MultiEdit` | `post_validate` | Kural-taşıyan dosya editlendiyse `run_all_validators --quick` + coverage nudge | **Evet** (validator FAIL'de geri besler) |
| PostToolUse `mcp__sap-adt__*` | `post_tool_failure` | SAP işlemi yapısal-fail döndürünce patinaj-kesici eskalasyon merdiveni enjekte | Hayır (bağlam enjekte) |
| ConfigChange | `config_change_guard` | Seans-içi davranış-yüzeyi değişimi manifest-onaysızsa blokla | **Evet** |
| PreCompact | `pre_compact` | Compaction öncesi SESSION_NOTES/memory flush hatırlatması | Hayır (systemMessage) |
| SessionEnd | `watchdog_stop` | Watchdog daemon'ı kapat | Hayır |

### (a) Oturum-başı hook'ları

**`session_start`** (SessionStart) — İki iş yapar. Birincisi statik enjeksiyon: ADR
0005 yasak özeti (A/B/C/D), ilk yanıtın "Ekran Teyidi" formatıyla başlaması
zorunluluğu, ve ajan-takım çalışma modeli. İkincisi dinamik sağlık kontrolleri:

```text
D25 — 4 junction TEK TEK sağlam mı (core, .claude/{agents,skills,commands})
      kopuk junction sessiz semptom verir → "SAP-yazma yapma" uyarısı
Damga — kök CLAUDE.md yasaklar damgası kanonikle eş mi (junction-bağımsız anayasa)
D7  — settings.json + hook_shim.py template'ten sapmış mı (hash karşılaştırma)
F2  — behavior-manifest diff: kayıtsız/değişmiş davranış dosyası → BÜYÜK uyarı
Ö3  — DEV_CORE origin-geride mi (saatte 1 fetch, 2 sn timeout, cache'li throttle)
D20b— detached@stable ise sakin bilgi (yanlış origin-geride alarmı üretme)
```

Junction sorunu bulunursa hepsi ⛔ ile listelenir ve "guardrail eksik olabilir,
SAP-yazma yapma" notu eklenir. Manifest sapması varsa "bu oturumun çıktısına güvenme"
kuralı devreye girer.

**`tooling_radar_check`** (SessionStart) — `governance/tooling-radar.md`
frontmatter'ındaki `last-run` tarihini okur; `cadence-days` (varsayılan 21) geçtiyse
iş-arası bir tarama önerir. Bayat değilse sessizdir (normal oturumda maliyet yok).
Amaç, araç taramasının yalnız SAP'a dar kalmayıp genel ajan-verimlilik araçlarını
(tarayıcı-doğrulama, token-verim, arama, kod-zekâsı) proaktif yüzeye çıkarmasıdır.

### (b) Prompt-anı hook'ları

**`skill_injector`** (UserPromptSubmit) — Prompt'ta güçlü, az-yanlış-pozitif sinyal
ararken üç ayrı eksen tarar:

- `_STRONG`: SAP geliştirme sinyalleri (CDS yarat, RAP, BDEF, DTEL, tablo yarat,
  aktive et, ZSD###, `.conn_adt`, UI5 …). Yakalanırsa `sap-abap-dev` skill rehberini
  hatırlatır ve iş-türünü tespit eder.
- `_WORKTYPES`: iş-türü → **okunması zorunlu pre-flight checklist** eşlemesi. Örneğin
  RAP/BDEF → `playbook/checklists/rap-creation.md`, klasik ALV →
  `classic-dialog-creation.md` (§1 include-böl zorunlu), DDIC struct →
  `struct-creation.md`. Böylece o iş-türünün kuralları unutulmaz.
- `_BROWSER`: tarayıcı/UI-doğrulama sinyali (SAP'tan bağımsız) → token-verimli akışı
  dayatır (önce `run_ui5_linter`/`run_manifest_validation`, sonra `playwright-cli`,
  layout'u gözle değil sayıyla doğrula).
- `_STRUCTURAL`: yapısal kod-arama/refactor sinyali → `ast-grep` CLI'yı hatırlatır
  (ripgrep/Grep lexical körlüğüne düşmemek için).

Otomatik-event işaretleri (`<task-notification>`, sistem-bildirimi) filtrelenir —
bunlar kullanıcı-turn'ü değildir, yanlış-pozitif üretmezler. Sinyal yoksa sessizdir.

**`intake_triage`** (UserPromptSubmit) — Bir **geliştirme talebi / revizyon / FS /
Excel-ister / rapor isteği** niyeti (`_INTENT` regex) görülünce ITG protokolünü
(Bölüm 9) enjekte eder. Tasarım ilkesi (ADR 0022): hook **durum tutmaz ve sınıflandırma
yapmaz** — yalnız tetikler ve protokolü dayatır; kapsam-sınıflama (S0/S1/S2), konu
çıkarımı ve 3-eksen araştırmayı ajan yapar. `_MODULES` regex'i yalnız **kaba modül
ipucu** verir (SD/MM/FI/CO/PP/QM/PM/WM-EWM); kural-paketi fiilen mevcut modüllerde
(`_HAZIR_PAKETLER`) dosya adını söyler, yoksa "genel iskeletle ilerle" der.
`skill_injector`'a kardeştir: o obje-tipi→checklist, bu kapsam+modül+protokol —
ayrık sorumluluk.

### (c) Araç-öncesi guard — `pre_tool_guard` 12 RED-katmanı

`pre_tool_guard`, `Bash | Edit | Write | MultiEdit | mcp__sap-adt__*` araçlarından
önce koşar. Sıcak-yolda tüm kontroller string/regex'tir (dosya-sistemi taraması yok;
yaml okuma module-load'da bir kez cache'lenir). Katmanlar sırayla:

| # | Katman | Neyi engeller | Tetik |
|---|---|---|---|
| 1 | **Yasak-damga** | SAP-yazma tool'undan önce kök CLAUDE.md yasak damgası kanonikle eş değilse RED | SAP-yazma MCP tool'ları |
| 2 | **Bağlantı-tutarsızlığı** (ADR 0010) | `.conn_adt` ile MCP'nin canlı bağlantısı ayrışıksa (switch_tier yapılıp `/mcp restart` edilmediyse) ADT işlemi RED | `mcp__sap-adt__*` (ping hariç) |
| 3 | **Freeze-guard** (R10) | `project.yaml` `frozen_readonly_paths` köklerine yazma (Edit/Write hedefi veya Bash yazma-fiili) RED; okuma serbest | Edit/Write/Bash |
| 4 | **Özyinelemeli-silme** (R9) | `core`/junction, `.claude/{agents,skills,commands}`, `DEV_CORE` hedefli özyinelemeli silme/`clean` RED | Bash |
| 5 | **Sızıntı-commit kilidi** (F1) | `git add/commit` kapsamında core-path stage'leme RED (fikri-sermaye sızıntısı) | Bash |
| 6 | **Core-leak** (Ö5) | `core/`'a yazılan içerikte proje/müşteri izi (sistem adı, kullanıcı, müşteri) tespit edilirse RED — jenerik-olmayan içerik girmez | Edit/Write core hedefi |
| 7 | **applies_to eksik** (D21) | `standards/` veya `playbook/` altına YENİ `.md` yazımında `applies_to:` frontmatter yoksa RED | Write core hedefi |
| 8 | **Tehlike** (ADR 0005-C) | Transport bırakma/oluşturma ve package oluşturma endpoint/FM token'ları RED | Bash / MCP argümanı |
| 9 | **Inline-aktivasyon** | Bash içinde elle ADT activation endpoint POST'u (helper kullanmadan) RED — bu yol `activationExecuted`'ı parse etmez, sahte HTTP-200-OK üretir | Bash |
| 10 | **Yalın fiori-deploy** | `deploy_ui.py` dışında doğrudan `fiori deploy` RED — build yapmaz, eski dist'i "Successful" diyerek yükler | Bash |
| 11 | **App-içi npm-install** | UI app alt-dizininde `npm install/ci/add` RED — tooling `ui/` workspace köküne hoist'lu | Bash |
| 12 | Core-yazım taraması bütünü (6+7 birlikte core hedefine uygulanır) | — | — |

RED durumunda hook stderr'e sebebi + düzeltme yolunu yazar ve exit 2 döner (Claude'a
geri beslenir). Tehlikeli/tutarsız değilse sessizdir.

**`pull_before_edit`** (PreToolUse `Edit|Write`) — Yönetilen bir SAP source dosyasını
(`<source_root>/` altı, kaynak uzantısı) düzenlemeden önce, o objenin canlı güncel
hali bu seansta çekilmiş/yazılmış olmalıdır (ADR 0016). Değilse edit bloklanır ve
ajan önce `scripts/sap_sync_pull.py` ile çeker. Muafiyetler: SAP-source değil,
`ref_docs/`/`docs/`/`.tmp/`, dosya yok (yeni obje), git-dirty (üstünde çalışılan WIP
— pull onu ezmesin), session_id yok (fail-safe). Amaç: working-copy daima taze
canlıdan türesin → push, canlıdaki belgelenmemiş bir değişikliği sessizce ezmesin.

**`watchdog_launch`** (PreToolUse `Agent`) — Arka-plan ajan spawn edilince, SAP/VPN/MCP
kopmasından doğan sessiz stall'i Claude'a bağlı olmadan haber veren detached bir daemon
başlatır (seans başına tek daemon, heartbeat ile idempotent). Windows MessageBox +
`.tmp/watchdog-alerts.log` ALERT üretir.

### (d) Araç-sonrası hook'ları

**`post_validate`** (PostToolUse `Edit|Write|MultiEdit`) — Yalnız kural-taşıyan
dosyalar validator'ları tetikler (`.rules.md`, `governance/`, `standards/`,
`validators/`, `populate_*.py`, `sprint*`, `td_spec`). Üç davranış:

```text
1. UI manifest.json editlendi → check_ui_odata_refs.py hatırlat (statik cross-check)
2. list/report view.xml → check_list_view_grid.py (grid standardı, ADR 0008)
3. standards/playbook/governance/decisions + AGENTS/CLAUDE .md editi + güç-keyword
   (MUST/YASAK/ZORUNLU/BLOCKER) → ADR 0019 onboarding (5-adım) + 8-ölçüt RUBRIC +
   checklist ise check_rule_gate_coverage --strict hatırlat
4. Kural-taşıyan dosya → run_all_validators.py --quick; FAIL ise özet + "forward
   progress YOK, önce ihlali düzelt" (STOP kuralı) → exit 2 geri besler
```

Durum/izleme dökümanları (RESUME, SESSION_NOTES, package-registry) kural taşımaz →
`governance/` altında olsalar da heavy run atlanır (sıfır gürültü).

**`post_tool_failure`** (PostToolUse `mcp__sap-adt__*`) — Bir SAP ADT tool'u yapısal
hata döndürünce (`ok:false`, bilinen error değeri, `success:false`, reviewer BLOCKER)
kör deneme-yanılma döngüsünü sistemsel keser. Enjekte edilen eskalasyon merdiveni:

```text
1. Kör tekrar YOK; aynı objede en çok 3 deneme (yalnız geçici CSRF/lock için)
2. 3'te çözülmezse → ZORUNLU playbook/adt-*.md + lessons-learned + hata pattern araştır
3. Toplam 5 denemede olmazsa → DUR + lider/kullanıcı (ham hata + denenenler + bulgu)
4. Transport: hata mesajındaki numarayı ASLA kullanma
5. Guardrail ihlaliyse: kuralı değiştirme — yaklaşımı değiştir
6. Çözünce playbook güncelle (T1)
```

CDS-yaratma patinaj imzası (`ddls/df`, `is not locked`, `invalidlockhandle`)
görülürse generic değil spesifik "TEK CDS YARATMA" reçetesi eklenir.

### (e) Config / Compact / End

**`config_change_guard`** (ConfigChange) — Hooks/settings canlı reload olur ve proje
hook'ları onaysız çalışabilir; oturum-başı manifest kontrolü seans-içi değişimi
göremez. Bu hook her ConfigChange'de tetiklenir: davranış-yüzeyi dosyası
(`settings.json`, `.mcp.json`, `CLAUDE.md`, `project.yaml`, `hook_shim.py`,
`.claude/rules/`) manifest-onaysız değiştiyse **bloklar** (exit 2); değilse denetim
izine yazar (`.tmp/config-changes.log`). F2'nin runtime bacağıdır.

**`pre_compact`** (PreCompact) — Compaction öncesi, aktif paketin SESSION_NOTES'una
son durumu ve önemli kalıcı bilgiyi memory'ye yazmayı hatırlatır. `systemMessage`
kanalıyla kullanıcıya gösterilir (PreCompact `additionalContext` kabul etmez).

**`watchdog_stop`** (SessionEnd) — Watchdog daemon'ı kapatır.

---

## 7. Kalite Kapıları: Validator + Reviewer + Coverage

Enforcement'ın ikinci ayağı, deterministik (LLM-bağımsız) Python validator'larıdır.
İki farklı giriş noktası vardır ve birbiriyle karıştırılmamalıdır:

| | `run_all_validators.py` | `run_review.py` |
|---|---|---|
| Amaç | Repo-geneli sağlık taraması | Tek SAP-yazma işi öncesi pre-flight |
| Kapsam | Tüm proje (kural-taşıyan artefaktlar) | Belirli `--task` + `--artifact` |
| Ne zaman | Oturum-başı `--quick`, `post_validate`, CI, gün-sonu | SAP'a create/push/activate ÖNCESİ |
| Çıktı | OK / N ihlal (exit 0/1) | PASS / WARNING / BLOCKER verdict |
| Tetik | Manuel + `post_validate` hook | Ajan/gateway çağırır (ADR 0006) |

**`run_all_validators.py`** iki modda koşar. **PROJE modu** (`project.yaml` var):
scope=project+both validator'lar + profil-filtreleri + `scripts/validators-local/*`
keşfi. **CORE modu** (project.yaml yok, örn. DEV_CORE CI): yalnız scope=both
statik validator'lar; proje-bağlamı isteyenler SKIP edilir. Her validator bir profil
etiketi taşır (`applies_to`) — örneğin RAP validator'ları yalnız
`s4_private/s4_public/btp_abap` profillerinde koşar, `ecc`'de atlanır. Örnek zincir:
KESİN YASAKLAR damgası (HARD, ADR 0005), core-sızıntı kilidi, paket naming, liste=grid
(HARD, ADR 0008), filtre/VH deseni (HARD, FE-32), kural↔gate coverage (HARD, ADR 0019).

**`run_review.py`** (ADR 0006 — Reviewer Agent Pattern), coordinator/gateway SAP
yazmadan önce çağırır. `TASK_VALIDATORS` sözlüğü her görev-tipini bir validator
zincirine eşler ve her validator'a bir varsayılan **severity** verir:

```text
cds_creation      → window_function(BLOCKER) + currency_ref(BLOCKER) +
                    deprecated_annotations(WARNING) + released_objects(WARNING) + ...
table_update      → struct_field_dtel_active(BLOCKER) + table_field_drop(BLOCKER) + ...
class_push        → method_param_type_c(BLOCKER) + amdp_apostrophe(BLOCKER) +
                    docu_itf_line_width(BLOCKER) + decimal_write_to(WARNING) + abaplint(WARNING)
rap_bdef_creation → rap_managed_etag(BLOCKER) + audit_fields_autofill(WARNING)
itg_s2_signoff    → check_itg_signoff(BLOCKER)   ← ITG S2 gate (ADR 0022)
```

Verdict hesabı basittir ve tek yönde eskalasyondur:

```text
BLOCKER count > 0  → verdict BLOCKER → SAP yazma YASAK, düzelt + tekrar review (exit 1)
WARNING count > 0  → verdict WARNING → yazabilirsin AMA kullanıcıya bildir  (exit 0)
aksi               → verdict PASS    → devam edebilirsin                    (exit 0)
--strict           → WARNING'i de BLOCKER say
```

Her görev-tipi ayrıca bir **manuel checklist** (`playbook/checklists/<task>.md`) referansı
üretir — deterministik validator'ın göremediği, LLM'in okuması gereken semantik kontroller.

**`check_rule_gate_coverage.py`** (ADR 0019, "keystone") coverage-check'tir. İlke:
*her kural bir gate'le zorlanmalı; gate'lenmemiş kural ≈ kuralsızdır.* Bu script, bir
kuralın "BLOCKER der ama arkasında çalışan script yok" durumunu (sahte-WIRED çürümesi)
otomatik yakalar — elle-bakımlı eşleme tutulmaz, hesaplattırılır. Karşılaştırılan
kaynaklar: (1) checklist tablo satırlarındaki `check_*.py` iddiaları, (2)
`scripts/validators/check_*.py` dosya varlığı, (3) `run_all_validators` +
`run_review` içinde geçen WIRED küme, (4) gate'in `# ENFORCES: <rule-id>` beyanı.

```text
3-EKSEN (ADR 0019):  (a) gate dosyası VAR mı
                     (b) bir runner'a WIRED mı (run_all / run_review)
                     (c) kırmızı-fixture ile test ediliyor mu (her gate kendi sorumluluğu)

Bulgu sınıfları:
  MISSING    — checklist gate adı verir ama dosya YOK (en ciddi: sahte-WIRED)
  ORPHAN     — script VAR ama hiçbir runner'da DEĞİL (wire-edilmemiş)
  UNDECLARED — WIRED ama `# ENFORCES:<id>` beyanı yok (binding eksik)
```

Bulgu varsa exit 1 (HARD — forward progress yok). Bu, checklist'te bir satırın gate
iddia edip gate'in gerçekte bulunmaması riskini kapatır.

**Kritik ilke — "checklist ≠ wired validator, bozuk-girdiyle test et":** Bir gate'in
sürekli PASS dönmesi onun doğru çalıştığını kanıtlamaz; gate yanlış-kablolanmış veya
no-op olabilir. Her gate, kasıtlı bozuk bir fixture (kırmızı-girdi) ile test edilerek
gerçekten FAIL üretebildiği doğrulanır. Coverage-check (a)+(b)+binding'i denetler;
fixture-varlığı gate'in kendi (c) sorumluluğudur. (Operasyonel karşılığı: Bölüm 14.3.)

---

## 8. Kural Mimarisi (L1-L4) ve SORU 0

Kurallar dört katmana ayrılır (ADR 0003 + 0020). Katman, bir kuralın **kapsamını** ve
**yaşadığı yeri** belirler:

| Katman | Konu | Yer | Örnek |
|---|---|---|---|
| **L1** | Agent davranışı (git, ADT işlem sırası, oturum protokolü) | `AGENTS.md` (core) | "push öncesi kullanıcı onayı al" |
| **L2** | Stabil kurumsal standartlar (naming, coding, UI, doc format) | `standards/` (core) | naming regex, RAP kodlama |
| **L3** | Operasyonel pattern (ADT pattern bankası, lessons-learned) | `playbook/` (core) | "TEK CDS YARATMA" reçetesi |
| **L4** | Paket-spesifik (prefix, bağımlılık, istisna) | `<source_root>/<MODULE>/<PKG>/.rules.md` (PROJE reposu) | `ZSD001_CLC` prefix kuralı |

L1-L3 metodolojidir ve `core/`'da yaşar (tüm projelere junction'la gelir); L4
proje-özeldir ve proje reposunda kalır. Proje-özel overlay kapıları da vardır:
`playbook-local/`, `standards-local/`, `scripts/validators-local/`.

**AGENTS.md (L1)** git ve ADT-infra davranışını tanımlar: kısa branch → push → PR →
CI yeşil → merge; `git push --force` / `--no-verify` kullanıcı açıkça istemedikçe
yasak; push öncesi her zaman kullanıcı onayı; geçici script → `TempScripts/`
(gitignored). ADT işlem sırası ve infra kuralları da buradadır.

### SORU 0 — Yeni bilgi nereye yazılır

Bir bilgi öğrenildiğinde ilk karar "bu metodoloji mi, projeye mi özel?" sorusudur.
Karar ağacı:

```text
SORU 0: Bu bilgi metodoloji mi, projeye mi özel?
  ├─ Metodoloji (pattern, validator, hook, standart, ADT dersi, checklist satırı)
  │     → DOĞRUDAN core'a yaz. Yazarken:
  │       • genericize: ZSD0xx → ZSD001 örneği; sistem/kullanıcı/müşteri → placeholder
  │       • link: core-içi link CORE-göreli; core → proje link YASAK
  │       • profil etiketi: applies_to hangi profiller? (kanıtsız genişletme YOK)
  └─ Proje işi (paket, iş kuralı, müşteri süreci, bağlantı, sprint)
        → proje reposu (SORU 1-3 ağacı; L4 .rules.md aynen)

SORU 1: Tek paket mi, tüm proje mi?          → tek paket = L4 (.rules.md)
SORU 2: Tipi? davranış=AGENTS · standart=standards · nasıl-yaparım=playbook · karar=decisions
SORU 3 (L3): dar obje-tipi → playbook/adt-<tip>.md · cross-cutting → lessons-learned.md
```

Bu ağaç, `pre_tool_guard`'ın core-leak (Ö5) ve applies_to (D21) katmanlarıyla zorlanır:
core'a proje-izi taşıyan içerik veya profil-etiketsiz standart/playbook yazımı bloklanır.

### T1-T11 Trigger'ları — hangi tetik hangi hedefe yazar

Yeni bilgi belirli tetiklerle kalıcılaşır. Özet:

| # | Tetikleyici | Hedef |
|---|---|---|
| T1 | ADT işlemi başarısız denemelerden sonra başarılı oldu | `playbook/<obje-tipi>.md` (çalışan + denenen-başarısız) |
| T2 | Playbook'ta olmayan senaryo başarıyla işlendi | Yeni section `playbook/` |
| T3 | Kullanıcı kural koydu | Davranış → AGENTS.md; standart → standards/; pakete özel → `.rules.md` |
| T4 | Kullanıcı trigger-phrase kullandı | `lessons-learned.md` recurrence + kod gate öner |
| T5 | Yeni paket / naming kararı | `.rules.md` (bootstrap script) |
| T6 | TempScripts'te çalışan script kalıcı lazım | core `scripts/`e taşı (genericize) + playbook ref |
| T7 | Mimari karar | Metodoloji → core `governance/decisions/NNNN-*.md`; proje → proje reposu |
| T8 | Paket-spesifik bağımlılık/istisna | `.rules.md` "Bilinen İstisnalar" |
| T9 | Script kullanıldı ama playbook referansı yok | İlgili playbook'a pattern + script ref |
| T10 | Patinaj/hata yakalandı | Düzelt + playbook (T1) + "reviewer yakalar mıydı?" → validator/checklist |
| T11 | Tekrar-eden tuzak / yeni iş-türü | Karar ağacı: validator / checklist / hook / pre_tool_guard (playbook notu YETMEZ) |

### Kural nasıl eklenir (ADR 0019 onboarding)

Yeni/değişen bir kural, `post_validate` hook'unun hatırlattığı 5-adım onboarding'ten
geçmeden "eklenmiş" sayılmaz:

```text
(1) GÜÇ-ETİKETLE      — MUST / MUST-NOT / SHOULD / MAY (belirsiz güç = uygulanamaz)
(2) ENFORCEMENT-SEÇ   — otomatikleştirilebilir mi, yargı mı?
(3) BAĞLA             — gate + kırmızı-fixture (otomatik) VEYA reviewer + checklist-üyeliği (yargı)
(4) STABİL-ID VER     — kural-id (ör. FE-32, BE-26, C-ITG-01) + gate `# ENFORCES:<id>` beyanı
(5) COVERAGE-CHECK    — check_rule_gate_coverage temiz mi (MISSING/ORPHAN/UNDECLARED yok)
```

Ayrıca 8-ölçütlü metin-kalitesi rubriği uygulanır: atomik, güç-açık, denetlenebilir
(pass/fail), kapsam-belli, tek-ev (canonical, tekrar değil), bağımsız-anlaşılır
(+gerekçe), stabil-ID, güncel-çelişkisiz.

---

## 9. İş-Alım: Intake Triage Gate (ITG)

ITG (ADR 0022), bir geliştirme talebinin alım-sürecini standartlaştırır: kapsamına
orantılı, kişiden bağımsız (tutarlı), kanıtlı. `intake_triage.py` hook'u bir
geliştirme-talebi/revizyon/FS/Excel-ister/rapor niyeti görülünce protokolü zorunlu
enjekte eder (Bölüm 6-b). Çekirdek ilke: ajan her domain'i ezbere bilmez — beklenti bu
değildir; iş geldiğinde onu **sınıflar → isterlerden bilmesi gereken konuları çıkarır →
hedefli araştırır → ancak bilgilendikten sonra** değerlendirir.

### İki dik eksen

Bir iş **iki bağımsız eksende birden** yaşar; karıştırılmaz:

```text
① Fonksiyonel modül ekseni (NE iş?)  : SD / MM / FI / CO / PP / QM / PM / WM-EWM
     → intake_triage hook kaba ipucu verir; kesin modülü ajan belirler.
     → modül kural-paketi (playbook/modules/<kod>.md) varsa OKUnur.
② Teknik/kodlama-tipi ekseni (NASIL?) : klasik ABAP / RAP / Fiori-UI5 / CDS / DDIC
     → skill_injector hook obje-tipi checklist'ini + standardı ZATEN enjekte eder.

Örnek: "SD modülünde yeni RAP raporu"
   ① SD kural-paketi (availability/pricing araştır, satış-org sor)
   ② rap-creation checklist (BDEF/CDS syntax, aktivasyon)
   İki hook birbirini çakışmadan tamamlar.
```

**Persona = kural-paketi, "act as X" DEĞİL.** Modül kural-paketi bir bilgi-deposu
değildir; yapılandırılmış bir aktivasyondur — hangi objeyi kontrol et, hangi soruyu
sor, hangi kaynağı araştır. Uzmanlık kaynak-zincirinden çıkar (persona-placebo değil).

### 6 adımlı protokol

```text
1. SINIFLA — iki dik eksen + KAPSAM (S0/S1/S2); gerekçesini bir cümleyle yaz
2. Modül kural-paketini OKU (varsa playbook/modules/<modül>.md)
3. İSTERLERDEN KONU ÇIKAR — her anlamlı alan bir domain-konusu doğurur
       ("kullanılabilir stok" → availability/ATP; "döviz/tutar" → currency conversion)
4. 3-EKSEN ARAŞTIR (bilgilen — sonra değerlendir):
       (a) domain bilgisi (docs-MCP/resmi kaynak; syntax TAHMİN EDİLMEZ)
       (b) canlı sistem / ilişkili kod (adt_where_used + adt_package_contents → harita,
           sonra adt_get → derin oku; reuse mi yeni mi + blast-radius + tutarlılık)
       (c) kurumsal hafıza / prior-art (memory + lessons-learned + SESSION_NOTES)
5. KANITLI DEĞERLENDİR — reuse + tutarlılık + geçmiş-ders + risk; TAHMİN YASAK
6. KAPSAM-ORANTILI SORU + AKSİYON
```

Enine kesen kalite kilidi (atlanamaz): her eksenin çıktısı kanıtlı olmalı; bir Z-obje
hatırlanıyorsa canlı-doğrula (hafıza=hipotez, canlı=otorite; ADR 0016); prior-art
"sanırım yaptık" değildir — referansı bul + doğrula, yoksa "yok" say.

### Kapsam sınıfları

| Sınıf | Nedir | Örnek | Akış ağırlığı |
|---|---|---|---|
| **S0 · nokta-düzeltme** | tek alan/label/mesaj; davranış değişmez | "şu kolon başlığı yanlış" | HAFİF: where-used → fix → bug-gate. Soru yok, artefakt yok |
| **S1 · lokalize** | tek app/rapor/CDS içi davranış değişimi | "bu rapora X kolonu ekle" | ORTA: kısa etki analizi + hedefli soru + fix + bug-gate |
| **S2 · kapsamlı** | yeni program/çok-obje/cross-stack/yeni sprint | "yeni sipariş-kalem raporu" | TAM: tam zincir + intake-artefaktı + mutabakat |

Sınır belirsizse üst sınıfa yuvarlamak değil, en makul sınıfı gerekçelemek esastır;
over-triage (küçük işe ağır süreç) de anti-pattern'dir.

### S2 sign-off gate

S2 (kapsamlı) bir iş, SAP-yazmasına geçmeden önce sabit-şemalı bir **intake-artefaktı**
üretir ve kullanıcı mutabakatı alır. Şema (`playbook/intake-triage.md`):

```text
# INTAKE — <kısa-ad>  (tarih)
- Modül / iş-tipi / KAPSAM: SD / rapor / S2  (gerekçe: ...)
- İstenen (özet):
- Çıkan domain-konuları: [konu → araştırma özeti (a/b/c eksen)]
- Etkilenen objeler (canlı-doğrulanmış): [obje → reuse/yeni/değişir → blast-radius]
- Prior-art: [bulundu: <ref> / yok]        ← ZORUNLU alan (aramayı mecbur kılar)
- Kabul kriterleri (EARS): "<olay> olduğunda sistem <sonuç> yapmalı"
- Açık kararlar / riskler:
- MUTABAKAT: [ ] kullanıcı sign-off
```

Bu artefakt `check_itg_signoff.py` ile deterministik doğrulanır (run_review
`--task itg_s2_signoff`, severity BLOCKER). Kontroller: zorunlu alanlar (KAPSAM,
etkilenen objeler, prior-art, kabul kriterleri) dolu mu; prior-art alanı
"bulundu:<ref>" veya "yok" içeriyor mu (boş bırakılamaz); MUTABAKAT satırında `[x]`
işareti var mı. Herhangi biri eksikse exit 1 → BLOCKER → SAP-yazma yasak. Gate,
`# ENFORCES: C-ITG-01..04` beyanıyla ADR 0019 coverage'a bağlıdır.

Kabul kriterleri EARS kalıplarıyla yazılır (Event-driven / Unwanted / State-driven /
Ubiquitous) ve INVEST/DoR ile test-edilebilir olmadan build başlamaz; backend ve
frontend ayrı DoR + ayrı bug-checklist taşır.

---

Aşağıdaki bölümler (10–14), canlı-çekirdek mimarisinin işletim katmanını tarif eder:
SAP'ye yazan araç yüzeyi, kurumsal hafıza, çok-ajanlı çalışma, GitHub akışı ve sağlık
taraması. Anlatım olgusaldır — her iddia mevcut bir tool/rol/repo/dosyaya dayanır.

## 10. SAP ADT MCP Sunucusu

SAP ABAP Development Tools (ADT) işlemleri, `stdio` transport'lu bir MCP sunucusu üzerinden
typed tool olarak sunulur (`mcp_servers/sap_adt/`; giriş `server.py`, kayıt `tools/` altındaki
`atom.py` · `composite.py` · `query.py` dekoratörleriyle). Karar gerekçesi ADR 0007: tek-obje
yaratım/aktivasyon/okuma gibi işlemler serbest-metin shell komutu yerine, dönüşü yapısal JSON
(`{ok: bool, ...}`) olan ve guardrail'i sunucu tarafında zorlayan araçlarla yapılır.

### 10.1 Tool envanteri (işlev gruplarına göre)

| Grup | Tool | İşlev | Yazma? |
|---|---|---|---|
| **Okuma / Analiz** | `ping` | Sunucu canlılık + versiyon + repo kökü | Hayır |
| | `adt_get` | Obje varlık + metadata + (opsiyonel) source; XML-DDIC tipleri ayrı okunur | Hayır |
| | `adt_search_objects` | Ad/wildcard ile obje arama (tip filtreli) | Hayır |
| | `adt_where_used` | Bir objeyi referanslayan objeler (etki/blast-radius) | Hayır |
| | `adt_table_read` | Tablo verisi okuma (ADT data preview); ADR 0011 PII guard'a tabi | Hayır |
| | `adt_package_contents` | Paket içeriği listeleme | Hayır |
| | `adt_lock_check` | Obje kilitli mi (best-effort metadata probe) | Hayır |
| | `adt_transport_list` | Kullanıcının değiştirilebilir/serbest transport listesi | Hayır |
| | `adt_syntax_check` | Aktive etmeden inactive-sürüm sözdizimi kontrolü | Hayır |
| | `adt_atc_check` | ATC statik kod kontrolü (Clean ABAP/perf/güvenlik) | Hayır |
| **Yaratım / DDIC** | `adt_post_shell` | Boş Z obje shell'i (source'suz, inactive) | Evet |
| | `adt_domain_create` | Domain create + activate + verify (composite) | Evet |
| | `adt_dtel_create` | Data element create + activate + verify; 4 label zorunlu | Evet |
| | `adt_struct_create` | Structure (INTTAB) create + activate + verify | Evet |
| **Aktivasyon / Push** | `adt_push_source` | Mevcut objeye source gövdesi push (reviewer pre-flight ile) | Evet |
| | `adt_activate` | Tek obje VEYA atomik çoklu-obje aktivasyon (tek `/activation` POST) | Evet |
| | `adt_delete` | Z/Y obje silme (standart obje reddedilir) | Evet |
| **Servis / Yürütme** | `adt_publish_service` | OData V2 service binding (SRVB) republish → `$metadata` tazeleme | Evet |
| | `adt_classrun` | `IF_OO_ADT_CLASSRUN` sınıfı çalıştırma (F9-run muadili) | Evet (yürütme) |

Okuma tool'ları hiçbir koşulda SAP'ye yazmaz; bu ayrım hem araç setinde hem de ajan
tool-allowlist'lerinde (bkz. Bölüm 12) fiziksel enforcement'ın temelidir.

### 10.2 Sunucu tarafı guardrail'ler (hardcoded, bypass yok)

Guardrail'ler her HTTP çağrısından ÖNCE çalışır; ihlalde `GuardrailViolation` yükseltilir ve
tool `{ok: false, error: "guardrail_violation", code, message}` döner. Ajanın "hatırlamasına"
bırakılmaz — kuralın kaynağı koddur (`guardrails.py`, `data_guard.py`).

| ADR | Kural | Kod | Uygulama noktası |
|---|---|---|---|
| **0005-A** | Standart obje yaratma/silme yasak — Z/Y customer namespace zorunlu (lock objeleri için E+Z/Y meşru) | `ADR_0005_A` | `require_customer_namespace`, `reject_standard_delete` |
| **0005-C** | Transport zorunlu; asla varsayılmaz (önce `adt_transport_list` + kullanıcı teyidi) | `ADR_0005_C` | `require_transport` |
| **0005-D** | Z obje TR text zorunlu; DTEL 4 label (short/medium/long/heading) dolu | `ADR_0005_D` | `require_tr_text`, `require_all_labels` |
| **0010** | Mutasyon (create/push/activate/delete) yalnız DEV tier'da; QA/PRD salt-okunur | `ADR_0010_TIER` | `require_writable_tier` (tier `.conn_adt`'den okunur) |
| **0011** | QA/PRD'de hassas tablo/alan okuma açık onay ister (KVKK); DEV muaf | `ADR_0011_PII` | `require_data_access` (affirmative kelime; muğlak "dene/çek" yetmez) |

ADR 0011 hassas-hedef deseni müşteri/iş-ortağı/adres, HR/bordro, banka/ödeme ve vergi-no
(TCKN/VKN/STCD/IBAN) tablo ve alanlarını kapsar; eşleşmede `acknowledge_risk=True` + onay
kelimesi olmadan okuma reddedilir.

Guardrail'e ek iki **bağlam-tutarlılık backstop'u** cache'li client üzerinde çalışır: (a)
`_guard_binding_current` — `.conn_adt` `switch_tier` ile değişip MCP `/mcp restart` edilmediyse
(client eski sisteme bağlı kalmış) ADT işlemini reddeder (ADR 0010; yoksa "write DEV der, istek
QA'ya gider" felaketi); (b) `_guard_module_current` — uzun-ömürlü MCP süreci `sap_client.py` disk'te
güncellenmişken bayat kodu bellekte çalıştırıyorsa reddeder. Her iki kontrol de kendisi kırılırsa
fail-open davranır (asıl katman hook `pre_tool_guard`).

### 10.3 Composite create + readback (activated-yalanına karşı)

Temel sorun: bir yazımın SAP tarafında "ok" dönmesi, objenin gerçekten aktif ve doğru içerikle
oturduğu anlamına gelmez (aktivasyon eksik/kısmi kalabilir, aktif sürüm push edilenin gerisinde
kalabilir). Sunucu bunu iki mekanizmayla ele alır:

- **Composite atomik akış** (`adt_domain_create` / `adt_dtel_create` / `adt_struct_create`):
  guardrail → pre-check (varsa `already_exists` ile dur) → create → `activate` → **verify**
  (`get_object_metadata` + `adtcore:version="active"` regex). `existence != active` dersi gereği
  varlık kanıt sayılmaz; ek olarak `masterLanguage="TR"` metadata'dan doğrulanır (EN çıkarsa
  yüksek-sesli uyarı). Rollback politikası konservatiftir: activate başarısızsa obje inactive
  bırakılır, otomatik silinmez — çağıran karar verir.
- **Readback-gate** (`adt_push_source` + `adt_activate`): push edilen source `_LAST_PUSHED`
  kaydında `(name.upper(), type_key)` anahtarıyla tutulur; activate sonrası AKTİF source çekilip
  normalize-compare edilir. Fark varsa `content_verified=False` + `ok=False` (BLOCKER sinyali:
  "yazım tam oturmadı, re-push/re-activate gerekli"). `adt_delete` sonrası da varlık readback'i
  yapılır — obje hâlâ varsa silme "oturmadı" sayılır. Anahtar `(ad, tip)` çiftidir; sadece isimle
  key'lemek DDLS ve BDEF çakışmasında sahte-mismatch üretir (CDS kaydını BDEF push'u ezer).

### 10.4 Reviewer pre-flight (ADR 0006)

Yazma tool'ları source'u geçici dosyaya yazıp `scripts/validators/run_review.py`'ı otomatik
çağırır. Verdict BLOCKER ise push reddedilir (`reject_payload`); WARNING ise geçer ama yanıta
`reviewer` alanı eklenir. `skip_reviewer=True` yalnız acil durum içindir. Tablo DROP'ları için
`ack_drop` parametresi hedefli/denetlenebilir alternatiftir: yalnız adı verilen alan DROP'ları
ACK-WARNING olur; adı verilmeyen DROP veya herhangi bir TYPE/RENAME değişimi hâlâ BLOCKER kalır.

### 10.5 MCP-vs-script karar kuralı

| İş türü | Kanal | Gerekçe |
|---|---|---|
| Tek obje yaratım/aktivasyon/push/silme/arama/where-used/lock/table-read | **MCP tool** | Typed dönüş + sunucu-tarafı guardrail + readback |
| CSV/batch işlemler, validator koşumu, sprint/spec gate'leri | **Script** | Toplu-işlem + orkestrasyon; MCP tek-obje granülaritesi uygun değil |

---

## 11. Kurumsal Hafıza (Memory) Sistemi

Hafıza katmanı, oturumlar arası süreklilik ile kanonik metodoloji arasında net bir ayrım
gözetir. Temel ilke: **memory = hatırlatıcı, core = kanonik** (`CLAUDE.core.md` §5).

### 11.1 Memory türleri

| Tür | Konum | İçerik |
|---|---|---|
| **user** | `~/.claude/CLAUDE.md` | Projeden-bağımsız kişisel tercih (metodoloji YAZILMAZ — çift-kaynak drift riski) |
| **feedback** | proje memory klasörü + `MEMORY.md` index | Davranış/çalışma-disiplini kuralları (nasıl-çalışırsın) |
| **project** | proje memory klasörü + `MEMORY.md` index | Projeye-özel work-state (paket durumu, iş çapaları, kararlar) |
| **reference** | `MEMORY.md` altında | Sabit başvuru bilgisi (kullanıcı e-postası, tarih vb.) |

Proje memory'si repo DIŞINDADIR (`~/.claude/projects/<slug>/memory/`), ancak dosya-bölgesi
modelinde (Bölge D) Bölge A gibi korunur: yalnız lider yazar.

### 11.2 memory-seed (yeni proje tohumu)

Repoya committed `claude/memory-seed/` klasörü **feedback** tipi memory'nin tohumudur.
`scripts/seed_memory.py` bu klasörü yeni geliştiricinin proje-hafıza klasörüne kopyalar →
geliştirici, proje sahibinin çalışma disiplinini devralır. Kapsam yalnız feedback'tir;
projeye-özel work-state tohuma dahil değildir. Kopyalama merge-safe'tir: hedefte zaten var olan
dosyalar ezilmez (yerel öğrenmeler korunur), index yalnız hedefte yoksa yazılır. Tohumdaki her
`feedback_*.md` bir çalışma kuralını (çoğu bir GATE ismiyle) taşır; `MEMORY.md` bunlara
tek-satır pointer verir.

### 11.3 Terfi mekanizması (metodoloji → core, pointer kalır)

Bir memory-feedback metodoloji-nitelikliyse (pattern, validator, hook, standart, ADT dersi,
checklist satırı) core'a TERFİ eder; memory'de yalnız tek-satır pointer kalır. Yön kararı
SORU 0 ağacıyla verilir: metodoloji → doğrudan core (genericize + `applies_to` profil etiketi +
core-içi link kuralı); proje işi → proje reposu. Terfi disiplini gün-sonu kontrolünde uygulanır.

### 11.4 Oturum-sürekliliği (artefaktta yaşar)

Süreklilik ajanların canlı bağlamında değil, kalıcı artefaktlarda yaşar (repo kaynağı, SAP
objeleri, task listesi, `SESSION_NOTES.md`, memory, git). Ajan bağlamı uçucudur — transcript
dosyası kalır ama otomatik resume yoktur. Bu yüzden yeni bilgi daima bir artefakta (core, proje
dosyası veya memory pointer'ı) düşürülür; "aklımda tutarım" geçerli bir süreklilik mekanizması
değildir.

---

## 12. Çok-Ajanlı Çalışma Modeli

Çalışma modeli, çok-ajanın okumada kazanıp yazmada kaybettiği araştırma bulgusuna dayanır
(`governance/agent-teams-operating-model.md`; ADR 0018). Takım okuma/araştırma-ağırlıklı,
gerçekten paralelleşen iş için açılır; seri/bağımlı iş solo yürütülür. Uzmanlaştırma persona
değil **grounding**'dir (zorunlu pre-flight okuma + kanonik desen pointer + scoped tool + skill).

### 12.1 Roller ve tool-düzeyi yetki ayrımı

| Rol | Lifecycle | SAP yazma | Görev |
|---|---|---|---|
| **lider** (ana oturum) | daimi | Koşullu (Bölüm 12.2) | Orkestrasyon, görev dağıtımı, kullanıcı muhatabı, tek committer |
| **adt-gateway** | STANDING | ✅ TEK yazıcı | Takım modunda tüm SAP yazımı (write tool'ları yalnız bunda) |
| **backend-expert** | LAZY (bounded feature-standing istisna) | ❌ | Tüm ABAP/RAP/CDS/DDIC; tasarım + yerel kaynak + read-only SAP |
| **frontend-expert** | LAZY (app-build'de bounded-standing) | ❌ | Tüm freestyle UI5 / OData V2; controller/view/i18n/manifest |
| **bug-expert** | HER ZAMAN LAZY + her review TAZE | ❌ (read-only) | Adversarial inceleme; verdict PASS/WARNING/BLOCKER |
| **sap-feature / sap-research** | LAZY | ❌ | Eski roster (uyumluluk); research repo kodunu da düzenlemez |

Yetki ayrımı **tool-allowlist ile fiziksel**tir, hook ile değil (hook çağıran-ajanı ayırt
edemez). Örnek: `backend-expert`/`frontend-expert`/`bug-expert` allowlist'inde `adt_push_source`,
`adt_activate`, `adt_*_create`, `adt_delete`, `adt_post_shell`, `adt_classrun` YOKTUR — bu roller
SAP'ye yazamaz. Yalnız `adt-gateway` bu yazma tool'larına sahiptir.

### 12.2 Single-writer (koşullu serializasyon)

Gateway'in tek amacı eşzamanlı yazıcıları serileştirmektir; tek yazıcı varken gereksizdir.

- **Solo (takım yok):** lider SAP'ye doğrudan yazar (run_review pre-flight + ADR 0005 yine geçerli).
- **Takım aktif (≥1 yazabilecek alt-ajan):** tüm SAP yazımı `adt-gateway`'den geçer; lider
  doğrudan yazmaz, gateway'e devreder. Ortak objeler (paylaşılan DDIC/CDS/tablo/API) lider
  tarafından sıralanır — tek ajana hazırlatılır, gateway bir kez yazar; paralel ALTER yaptırılmaz.

### 12.3 Bug-gate (expert → bug-expert → lider)

Model A, lider-aracılıdır (alt-ajan spawn edemez):

1. Expert substantive build'i bitirince lider'e `BUG_GATE_READY` + diff + niyet/spec + blast-radius
   yollar (commit/kabul ÖNCESİ).
2. Lider **TAZE** bir bug-expert spawn edip diff'i besler (önceki bug context'i kirlilik sayılır →
   her review taze).
3. Verdict PASS/WARNING/BLOCKER (ADR 0006 dili): PASS → lider commit; BLOCKER/EKSİK → lider
   Expert'i `SendMessage` ile yeniden devreye alır (zorunlu fix).

Kapsam = diff + blast-radius. Bulgu tipi üçlüdür: **HATA** (kod bozuk) / **EKSİK** (kod çalışır ama
must-do/UX karşılanmamış) / **ÖNERİ** (checklist-dışı, bağlayıcı değil, verdict'i etkilemez). HATA+EKSİK
= checklist must-do → zorunlu fix; builder "önemsiz" diyemez, yalnız kanıtla "bu ihlal değil"
itirazı yapabilir. bug-expert read-only'dir → "düzeltilmeli" der, fix'i Expert yapar. Büyük/riskli
diff'lerde lider takdiriyle çok-bug-expert paneli (disjoint partition ya da diverse-lens) açılabilir;
panel üyeleri de tazedir.

### 12.4 İletişim ve süreklilik

Lider = hub; expert/gateway lider'e `SendMessage` ile rapor eder, ajanlar kendiliğinden
senkronlanmaz. Ajan brifingine `SendMessage({to:"main"})` eklenmezse rapor gelmez. Model-tiering
daima **declarative**'dir (frontmatter/spawn parametresi); hook/guard ile hard-enforce edilmez —
precision işinde tier-kilidi kaliteyi sessizce düşürür.

---

## 13. GitHub Mimarisi ve Çalışma Akışı

### 13.1 Üç repo ve rolleri

| Repo | Rol |
|---|---|
| `<ORG>/DEV_CORE` | Canlı metodoloji çekirdeği — junction'la tüm projelere yansır (ADR 0020) |
| `<ORG>/<PROJE_REPO>` | Proje reposu — SAP kaynağı, docs, project.yaml, governance |
| `<ORG>/.github` | Org-seviyesi varsayılanlar |

Proje, core'u fiziksel kopya olarak değil **junction** olarak taşır (`core`, `.claude/agents`,
`.claude/skills`, `.claude/commands`). Core içeriği proje reposuna commit'lenmez — ayrımı CI
zorlar (Bölüm 13.3).

### 13.2 Ruleset'ler ve stable-tag

| Ruleset | Kapsam | Etki |
|---|---|---|
| main-pr-required (active) | Her iki repo `main` | Doğrudan push yasak; değişiklik = branch → PR → CI yeşil → merge |
| stable-tag-lider-only | CORE `stable` tag | `stable` tag'ini yalnız lider ilerletir |

Yazma akışı trunk-based'tir: `main` tek uzun-ömürlü branch; kısa branch'ler aynı gün merge edilir.
Tek-kişi düzeninde `required_approving_review_count=0` olsa da PR yine zorunludur. Commit'ler
`core.hooksPath=scripts/git-hooks` gate'inden geçer (genericize-leak + link-audit + applies_to
şema).

### 13.3 CI (sızıntı + davranış-yüzeyi kontrolü)

`.github/workflows/` altında iki iş vardır:

- **Proje `guard.yml`** — iki job:
  - `core-leak`: tracked tree'de `core/**` veya `.claude/{agents,skills,commands}/**` görülürse
    FAIL (junction içeriği repoya girmiş = sızıntı, R1/D26).
  - `behavior-surface`: davranış-yüzeyi dosyaları (`CLAUDE.md`, `*/CLAUDE.md`, `.claude/*`,
    `.mcp.json`, `project.yaml`, `scripts/hook_shim.py`) — PR'da dokunuluyorsa görünür WARNING
    (lider incelemesi şart); `main`'e merge-OLMAYAN doğrudan push dokunuyorsa FAIL (yalnız
    lider-onaylı PR).
- **CORE `core-ci.yml`** — `gates` job'u pre-commit hook'unun sunucu aynasıdır (hook lokalde
  atlansa bile merge edilemez): `core_precommit.py --all` (tam-ağaç genericize+link+applies_to) +
  `run_all_validators.py` + `py_compile` derleme taraması. Bu job main-ruleset'e required_status_check
  olarak bağlanır.

### 13.4 Rollback (stable-tag + detached)

`stable` = bilinen-iyi commit; yalnız lider ilerletir (`git tag -f stable && git push -f origin
stable`, gate geçişlerinde). Core bir hatayla bir proje oturumunu bloke ederse:
`git -C <core> checkout stable` → tüm projeler anında bilinen-iyiye döner (session_start durumu
"detached@stable" olarak sakin raporlar). Onarım sonrası `git switch main`. Junction'a
dokunulmaz — rollback tamamen git işlemidir. Başka makine/PR'dan gelen core değişikliği makineye
tek yerden iner (`git -C <core> pull`); projelerde pull yoktur (junction).

### 13.5 Davranış-yüzeyi güvenlik duvarı + yabancı-repo misafir-modu

Davranış taşıyan dosya ya core'dan junction'la gelir ya behavior-manifest'te kayıtlıdır; değilse
RED ya da intake-gümrüğünden geçer (`CLAUDE.core.md` §8/§11). Davranış-yüzeyi yalnız lider-onaylı
PR ile değişir. Yabancı repoya ilk temas: önce Claude'suz `foreign_project_audit.py` pre-scan →
`--safe-mode` → kod-sınıfı (hooks/MCP) incelemesiz normal oturum açılmaz → `guest_mode.py` ile
`CLAUDE.local.md`. Değerli dış kural `intake/` karantinasına alınır → çakışma-analizi + canlı-test
→ PR. (Güvenlik/gizlilik açısından konsolide bakış: Bölüm 15.)

---

## 14. Sağlık ve Kalite Araçları

### 14.1 ix_doctor (7 katman)

`scripts/ix_doctor.py`, `sap_doctor`'un kardeşidir: "SAP bağlantısı sağlıklı mı?" yerine
"canlı-çekirdek kurulumu uçtan uca sağlıklı mı?" sorusuna bakar. Her kontrol bir kanıt-satırı
basar; katman durumu = kontrollerin en kötüsü (FAIL > WARN > PASS). Exit 0 = FAIL yok, 1 = en az
bir FAIL. SAP'ye default'ta ASLA çıkılmaz (`--live-sap` gerekir).

| # | Katman | Örnek kontroller |
|---|---|---|
| 1 | FS + bağımlılık | 4 junction gerçek core'a çözülüyor · managed-policy · plugin envanteri · CLI mevcudiyeti |
| 2 | Git | remote org tutarlı · `main == origin/main` · `stable` tag · hooksPath · global baseline · tree temizliği |
| 3 | GitHub-enforce | ruleset ACTIVE · CI yeşil · repo tree'de core-sızıntısı yok (gh CLI yoksa SKIP+WARN) |
| 4 | Claude katmanı | settings/shim template-drift (hash) · SHIM_SURUM · behavior-manifest ↔ ağaç · hook smoke · freeze-guard CANLI test |
| 5 | MCP / SAP | `.conn_adt` var + placeholder'sız · MCP server junction'dan erişilebilir · (`--live-sap`) canlı probe |
| 6 | Validators + perf | `run_all_validators` TAM PASS + süre · `session_start` < 1.5sn |
| 7 | İş-akışı smoke | memory (`MEMORY.md` dolu) · deploy-zinciri import-sağlığı · aktif paket `.rules.md` |

### 14.2 behavior_manifest (davranış-yüzeyi hash envanteri)

`scripts/behavior_manifest.py`, ajanın davranışını şekillendiren proje-lokal dosyaların
(CLAUDE.md, `.mcp.json`, `project.yaml`, `hook_shim.py`, `.claude/settings*.json`, nested
CLAUDE.md'ler) SHA-256 hash envanterini tutar. Manifest yalnız lider-onaylı PR ile güncellenir
(`generate`); `session_start` her oturum başında canlı ağacı manifest'le karşılaştırır → kayıtsız/
değişmiş dosya BÜYÜK uyarıdır. Junction'la gelen core içeriği (agents/skills/commands) manifest
DIŞIDIR — onların bütünlüğü core-git'in işidir; buradaki amaç PROJE-LOKAL sapmayı yakalamaktır.
Tespit post-load'dur; önleme çevre duvarındadır (Bölüm 13.5).

### 14.3 Enforcement-testi yaklaşımı (guard'ları bozuk-girdiyle sınama)

Sürekli PASS dönen bir kontrol, gerçekten bir şeyi zorladığının kanıtı değildir; guard'lar
bozuk-girdiyle test edilir. ix_doctor katman 4 bunu somutlaştırır: **freeze-guard CANLI testi**,
dondurulmuş köke sahte-Write stdin-JSON'u simüle eder (gerçek yazma YOK) ve exit 2 + RED mesajı
bekler — hem backslash hem forward-slash yol varyantıyla, çünkü guard'ın eski canonicalize hâli
bir varyantta sessizce yanlış-pozitif PASS veriyordu. Aynı ilke reviewer için de geçerlidir:
"checklist ≠ wired validator" — BLOCKER arkasında koşan bir script olduğu, kasıtlı bozuk girdiyle
doğrulanır. Bu yaklaşım, kuralın gate'lenmemişse kuralsıza denk olduğu ilkesinin (her kural
atlanamaz kurgulanmalı) operasyonel karşılığıdır.

---

## 15. Güvenlik, Gizlilik ve Uyumluluk

Bu bölüm, sistemin güvenlik ve veri-gizliliği açısından bilinmesi gereken davranışlarını
tek yerde toplar. Ayrıntılar ilgili bölümlerdedir.

### 15.1 Veri gizliliği (KVKK) — PII guard
Tablo verisi okuma (`adt_table_read`) sistem katmanına duyarlıdır (ADR 0011). Geliştirme
(DEV) katmanında serbesttir; kalite/üretim (QA/PRD) katmanında hassas tablo/alan (müşteri,
personel, banka, kimlik numarası vb.) için açık risk-kabulü ve onay kelimesi ister; muğlak
ifade yeterli değildir. Amaç, kişisel verinin denetimsiz dışa çıkmasını engellemektir.

### 15.2 Fikri-sermaye sızıntısı koruması
Çekirdek metodoloji, proje repolarına **gönderilemez** (junction ile görünür ama git'e
girmez). Bir `git add`/commit kapsamına çekirdek içeriği girerse eylem reddedilir; ayrıca
CI tarafında sunucu-seviyesinde ikinci bir kontrol vardır. Çekirdeğe yazılan içerikte
proje/müşteri kimliği tespit edilirse (genericize-guard) yazma reddedilir — çekirdek jenerik
kalır, müşteri kimliği dış-paylaşımda sızmaz.

### 15.3 Donmuş (salt-okunur) yedekler
Eski/arşiv kökler `project.yaml`'da `frozen_readonly_paths` ile işaretlenir. Bu köklere
her türlü yazma (Edit/Write/Bash) reddedilir; okuma serbesttir. Böylece dondurulmuş bir
yedek yanlışlıkla değiştirilemez. (Bu koruma, dönemsel enforcement-testleriyle gerçek yol
formatlarında doğrulanır — Bölüm 14.)

### 15.4 Davranış-yüzeyi güvenlik duvarı
Ajan davranışını değiştiren dosyalar (`CLAUDE.md`, `.claude/**`, `.mcp.json`, `project.yaml`,
hook giriş noktası) "davranış-yüzeyi" sayılır ve yalnız lider-onaylı PR ile değişir; oturum
içi değişiklikleri bir hook (ConfigChange) izler. Bir davranış-manifest'i (hash envanteri)
bu dosyaların beklenmedik değişimini yakalar.

### 15.5 Yabancı repoya ilk temas (misafir modu)
Bilinmeyen/dış bir projeye ilk bağlanışta, önce yapay-zekâsız bir ön-tarama (`foreign_project_audit`)
çalışır; sonra güvenli-modda (`--safe-mode`) oturum açılır ve o projeye özel geçici bir kural
dosyası (`guest_mode`) üretilir. Kod-sınıfı (hook/MCP) incelenmeden normal oturum açılmaz.
(İşletim akışındaki karşılığı: Bölüm 13.5.)

### 15.6 Denetim izi (audit trail)
Her SAP-yazımı ön-incelemeden (reviewer), her değişiklik PR + CI'dan geçer; git geçmişi +
davranış-manifest + oturum notları birlikte uçtan uca izlenebilirlik sağlar. Yanlış bir
değişiklik `stable` etiketine geri döndürülerek kurtarılabilir.

---

## 16. Onboarding: Yeni Geliştirici ve Yeni Proje

### 16.1 Yeni geliştirici (mevcut projeye katılım)
Ayrıntılı el kitabı: `DEV_CORE/ONBOARDING.md`. Özet akış:
1. Ön-koşullar: git yapılandırma temeli (`autocrlf=false`, `longpaths=true`, `defaultBranch=main`),
   Node/npm, `claude` CLI, GitHub kimliği, gerekli eklentiler.
2. Projeyi klonla → `python core/scripts/team_setup.py` (junction'ları kurar, hook yolunu
   ayarlar, hafızayı tohumlar).
3. `.conn_adt` bağlantı dosyasını doldur (şablon: `core/claude/conn_adt.template`).
4. Kurulumu doğrula: `python core/scripts/ix_doctor.py`.
5. Son oturum notunu oku, çalışmaya başla.

### 16.2 Yeni proje açma
Ayrıntılı el kitabı: `DEV_CORE/PROJECT_BOOTSTRAP.md` (STEP 0–6 + kabul kapısı). Özet:
- **STEP 0:** repo modu seç (`full` GitHub / `local` yalnız yerel git / `none` git'siz).
- `init_project.py` iskeleti üretir (yasaklar-damgalı `CLAUDE.md`, `project.yaml`, dizin yapısı).
- `team_setup.py` junction'ları + hook yolunu + hafıza tohumunu kurar.
- `project.yaml`'da profil (`sap_profile`, `release`, `master_language`, `source_root`) belirlenir.
- Kabul kapısı: sızıntı kontrolü, validator geçişi, junction sağlığı.
Yeni proje, çekirdek metodolojisinin tamamını junction'la devralır; yalnız kendi iş-bilgisini
(kural/paket/bağlantı) ekler.

---

## EK-A. Karar Kayıtları (ADR) Dizini
Sistem 22 mimari karar kaydı içerir (`DEV_CORE/governance/decisions/`). Öne çıkanlar:

| ADR | Konu |
|---|---|
| 0001 | Tek branch (PR-zorunlu modeliyle revize) |
| 0005 | Standart SAP nesne koruması + sistem-state yasakları (temel yasaklar) |
| 0006 | Reviewer (ön-inceleme) ajan deseni |
| 0007 | SAP ADT MCP sunucusu |
| 0008 | Liste ekranı grid (sap.ui.table) paritesi |
| 0009 | Ortak value-help CDS politikası |
| 0010 | Katman-bazlı salt-okunur guard (bağlantı-tutarlılığı) |
| 0011 | Veri-çıkarma / PII guard (KVKK) |
| 0012–0017 | Klasik ALV template, belge-kilidi, source-drift, UI doğrulama, agent takım |
| 0018 | Agent takım yapısı (katman + bug-gate) |
| 0019 | Kural-enforcement mimarisi (3-eksen coverage) |
| 0020 | Canlı-çekirdek junction mimarisi |
| 0021 | Temel yasaklar fiziksel-damga |
| 0022 | Intake Triage Gate (iş-alım katmanı) |

## EK-B. Terminoloji
- **DEV_CORE:** metodoloji çekirdeği reposu (tek kaynak).
- **junction:** Windows dizin bağlantısı; proje `core/` → DEV_CORE.
- **hook:** belirli bir olayda (oturum başı, prompt, araç öncesi/sonrası) otomatik çalışan script.
- **guard:** araç-öncesi denetim; kural ihlalinde eylemi reddeder (RED).
- **validator:** bir kaynağı/kuralı kontrol eden `check_*.py`; PASS/FAIL.
- **gate (kapı):** bir eylemin geçmesi için sağlanması gereken kontrol (validator/reviewer/hook).
- **reviewer:** SAP-yazımı öncesi çalışan ön-inceleme; PASS/WARNING/BLOCKER.
- **ITG:** Intake Triage Gate — geliştirme talebi alım/sınıflama katmanı.
- **profil:** projenin SAP türü (ecc/s4_private/s4_public/btp_abap); hangi kuralların geçerli olduğunu belirler.
- **stable etiketi:** çekirdeğin bilinen-iyi git noktası; rollback hedefi.
