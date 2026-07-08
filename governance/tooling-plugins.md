# Kurulu Plugin Envanteri — <PROJECT_NAME>

> **Amaç:** Aktif Claude Code plugin'lerinin ne işe yaradığı, **bizim hangi işimizde**
> kullanılacağı ve nasıl tetiklendiği. Yeni plugin kurulduğunda/kaldırıldığında bu dosya
> güncellenir. Kapsam = `governance/` (proje-geneli araç kaydı; `package-registry.md` gibi).

**Son güncelleme:** 2026-06-28 · **Kaynak marketplace:** `claude-plugins-official`

---

## 0. KURULUM — gerekli plugin'ler (clone/yeni geliştirici)

> Plugin'ler repo'da DEĞİL, makine/kullanıcı düzeyinde kuruludur → clone otomatik almaz.
> Tek komut (idempotent), `init_project.py`/`team_setup.py`/`/onboard` da çağırır:
>
> ```
> python scripts/setup_plugins.py          # eksik gerekli plugin'leri kur
> python scripts/setup_plugins.py --list   # durum
> ```
>
> **GEREKLİ (8):** `ui5` · `playwright` · `pyright-lsp` · `code-review` · `frontend-design` ·
> `claude-md-management` · `skill-creator` · `plugin-dev` — hepsi `claude-plugins-official`.
> Manuel: `claude plugin install <ad>@claude-plugins-official`. Plugin'ler **yeni oturumda** aktif.
> (Liste değişirse hem bu satırı hem `scripts/setup_plugins.py::REQUIRED`'ı güncelle.)

---

## 🔎 Yeni SAP MCP/skill ararken — İLK buraya bak

**Küratörlü katalog:** [`marianfoo/sap-ai-mcp-servers`](https://github.com/marianfoo/sap-ai-mcp-servers) — tüm SAP MCP server'ları + Claude skill'leri, resmi/topluluk ayrımlı, otomatik & güncel (günlük üretiliyor). Yeni bir araç/yetenek ihtiyacında keşif başlangıç noktası. (İncelendi 2026-06-09; Clean Core/ABAP/RAP girişleri değerlendirildi → bkz. aşağıdaki kıyas + `governance/research/`.)

---

## ⛔ ÖNCE — Plugin'ler yasakların ÜSTÜNDE değildir

Hiçbir plugin **ADR 0005 kesin yasaklarını** gevşetmez. UI5/SAP plugin'leri bazen
**CAP (Cloud Application Programming)** veya standart-obje varsayar; biz **ABAP RAP +
freestyle UI5** kullanıyoruz. CAP'e özgü öneriler (cds watch, srv/ db/ klasörü, CAP
annotation'ları) **bizde geçersiz** — ABAP RAP backend + kendi MCP/ADT akışımız esastır.
Plugin çıktısı yasakla çelişirse: DUR → kullanıcıya sun (bkz. `sap-abap-dev` skill TIER 0).

---

## 1. PROJEYE ÖZGÜ (SAP/UI5/Python) — asıl değer

### `ui5` — SAPUI5/OpenUI5 geliştirme
| | |
|---|---|
| **Sağladığı** | `ui5-mcp-server` MCP (npx `@ui5/mcp-server`) + 2 skill: `ui5-best-practices`, `ui5-best-practices-integration-cards` |
| **MCP tool'ları** | UI5 proje yaratma/doğrulama · **API reference sorgulama** (`get_api_reference`) · **UI5 linter** (`run_ui5_linter`) · tooling/versiyon bilgisi |
| **Bizde hangi iş** | Freestyle UI5 ekranları (voyage, container_report, sıradaki BOOKING UI). Control API'sini **tahmin etmeden** doğrulamak, lint ile best-practice kontrolü. ORDER'da yaşanan UI patinajını keser |
| **Ne zaman tetiklenir** | UI5/manifest/controller/view yazarken `ui5-best-practices` skill'i; API/lint gerektiğinde MCP tool |
| **Dikkat** | CAP entegrasyon bölümleri bizde geçersiz (ABAP RAP). Form kuralı (asla `SimpleForm`, hep `Form`+`ColumnLayout`) bizim `standards/03`'e uyumlu — uygula |

### `playwright` — tarayıcı otomasyonu / e2e doğrulama
| | |
|---|---|
| **Sağladığı** | İKİ kanal: (1) `playwright-cli` skill — terminal CLI (`.claude/skills/playwright-cli/`, `npm i -g @playwright/cli` + `playwright-cli install --skills`); (2) `playwright` MCP (`@playwright/mcp@latest`). |
| **Bizde hangi iş** | UI app'leri **localhost'ta** (`npm start`/`ui5 serve`) çalıştırıp gerçek tarayıcıda doğrulama: navigasyon, filtre, ALV kolonları, Excel export, **layout/hiza**. |
| **Ne zaman tetiklenir** | "UI'ı doğrula / ekran görüntüsü al / tarayıcıda bak / lokalde test" → `skill_injector` hook **token-verimli akış nudge'ı** enjekte eder (aşağıdaki sıra). |
| **Dikkat** | OData backend'e VPN gerekir; basic auth. 401/boş-liste → [[grid-ui lokal-çalıştırma]] reçetesi (lrep vs hesap-kilidi ayır). |

> #### ⚡ TOKEN-VERİMLİ AKIŞ (ZORUNLU sıra — vision-screenshot patinajını keser; ölçüldü: CLI MCP'den ~4x az token, 2026-06-13)
> 1. **ÖNCE tarayıcısız** — UI hatası / control-API / manifest için `ui5-mcp` `run_ui5_linter` · `run_manifest_validation` · `get_api_reference`. Çoğu kontrol tarayıcı gerektirmez; UI patinajının kökü "control API tahmini"dir.
> 2. **Tarayıcı gerekiyorsa `playwright-cli`** (skill) tercih — snapshot'ı **diske YAML** yazar, kısa komut gönderir (MCP tam accessibility ağacını context'e akıtır). MCP'yi yalnız kalıcı-durum/iteratif senaryolarda kullan.
> 3. **Layout'u GÖZLE değil SAYIYLA doğrula** — `snapshot --json` / `eval` ile `getBoundingClientRect` oku, **çakışma/hiza'yı KODLA** karşılaştır. "Alanlar çakışıyor mu / hizalı mı" sorusu deterministik+vision'sız çözülür (bu oturumdaki geo-satırı patinajının dersi).
> 4. **State'i `eval` ile sür** (model/handler'ı doğrudan çağır) — yavaş tıklama zincirini ve bozuk OData/401'i atlar.
> 5. **Görsel ŞARTSA** (grafik/canvas/ARIA'sız kontrol veya son göz kontrolü): yalnız **elementi** çek + **JPEG** (tam-sayfa PNG değil; ~1/5 token). MCP snapshot'a daima `target`+`depth` ver, tam-sayfa alma.
>
> Hatırlatma `scripts/hooks/skill_injector.py::_BROWSER` ile UserPromptSubmit'te otomatik enjekte edilir (SAP sinyalinden bağımsız).

### `pyright-lsp` — Python kod zekası
| | |
|---|---|
| **Sağladığı** | Pyright LSP (diagnostics/type-check). **Önkoşul:** `pip install pyright` veya `npm i -g pyright` |
| **Bizde hangi iş** | `scripts/validators/`, `mcp_servers/sap_adt/`, `populate_*.py`, `bootstrap_*.py` düzenlerken tip/hata erken yakalama |
| **Ne zaman tetiklenir** | `.py` dosyası düzenlenince otomatik diagnostics |
| **Dikkat** | Windows: konsol çıktısı ASCII-only kuralı hâlâ geçerli (bkz. `sap-abap-dev` operational-lessons) |

### `ast-grep` — yapısal (AST) kod arama/refactor
| | |
|---|---|
| **Sağladığı** | AST-tabanlı yapısal arama+rewrite, 26+ dil (Python, JS/TS). `npm i -g @ast-grep/cli` (binary: `ast-grep`/`sg`). **CLI seçildi, MCP DEĞİL** — MCP tool-şeması ~35-43× token; CLI 0 duran-maliyet (CLI-over-MCP ilkesi, playwright-cli deseni). |
| **Bizde hangi iş** | ripgrep/Grep'in **lexical körlüğü**: "şu imzalı tüm fonksiyon/method", "hatalı-handle'sız async", "tüm `populate_*`'da şu desen", toplu refactor/rename. `scripts/`+`mcp_servers/` (Python), UI5 controller (JS) audit/refactor. ripgrep↔pyright arası eksik orta katman. |
| **Kullanım** | `ast-grep -p '<pattern>' -l <py\|js\|ts> <path>` (meta-var `$X`, `$$$`); toplu rewrite `--rewrite '<yeni>'`. Düz metin yetiyorsa **Grep kalsın**. |
| **Ne zaman tetiklenir** | `skill_injector._STRUCTURAL` → yapısal arama/refactor sinyalinde nudge (recall; kur-bırak değil). 2026-06-13 tooling-radar ADOPT. |

---

## 2. GENEL GELİŞTİRME ARAÇLARI (proje-bağımsız ama faydalı)

| Plugin | Ne işe yarar | Bizde kullanım |
|---|---|---|
| `code-review` | Çok-ajanlı PR/diff review (`/code-review`, ultra=bulut) | Commit/PR öncesi kod kalite + bug taraması |
| `frontend-design` | Generic-olmayan, kaliteli frontend üretimi | UI5 ekran görsel kalitesi/iskelet fikri |
| `claude-md-management` | CLAUDE.md denetim/iyileştirme + oturum öğrenimi | Loader dosyamızın bakımı |
| `skill-creator` | Skill yaratma/iyileştirme/eval | Yeni project-skill (örn. `sap-abap-dev`) |
| `plugin-dev` | Plugin/skill/hook/command/MCP geliştirme (7 skill) | Kendi plugin/skill'lerimizi kurarken |

---

## 3. KARAR — "Bu iş için hangi araç?"

| İş | Araç |
|---|---|
| ABAP/CDS/RAP/DDIC yaz veya değiştir | `sap-abap-dev` skill → MCP `sap-adt` / script (ADR 0005/0006/0007) |
| UI5 control API / best-practice / lint | `ui5` (skill + `ui5-mcp-server`) + `standards/03` |
| UI'ı tarayıcıda çalıştır/doğrula/ekran görüntüsü | `playwright` + `/verify` veya `/run` |
| FS/TS/KD diyagramı (akış/sequence/ER/state) | `mmdc` (Mermaid) via `scripts/doc_tools.py` |
| Eğitim slaytı (canlı-geçiş sunumu) | `marp` via `scripts/doc_tools.py marp deck.md pdf` |
| TS§4.5 / KD§6 alan tablosu | `python scripts/gen_field_table.py <cds>` (CDS'ten, OCR değil) |
| Python script düzenle | `pyright-lsp` diagnostics |
| Commit/PR kalite kontrol | `code-review` |
| CLAUDE.md/skill bakımı | `claude-md-management` / `skill-creator` / `plugin-dev` |

> Yeni plugin kurulursa: kur → bu envantere satır ekle → ilgili katmana (standards/playbook)
> kullanım notu düş → CLAUDE.md §8'de zaten bu dosyaya pointer var.

---

## 4. SETTINGS.JSON HOOK'LARI (harness otomatik-zorlama — ADR 0005/0006)

`.claude/settings.json` (paylaşılan) içinde **deterministik gate** hook'ları aktif.
Amaç: kod gate'lerini "agent elle hatırlasın" yerine harness'in otomatik zorlaması.

| Hook | Tetik | Davranış | Script |
|---|---|---|---|
| **SessionStart** | startup/resume/compact | ADR 0005 yasak özeti + §2 Ekran Teyidi protokolünü context'e enjekte eder (compaction'a dayanıklı) | `scripts/hooks/session_start.py` |
| **PostToolUse** (`Edit\|Write\|MultiEdit`) | governance/standards/validator/spec/`.rules.md`/`populate_*.py` düzenlemesi | `run_all_validators.py --quick` koşar; **OK → sessiz**, **FAIL → stderr özet + exit 2** (CLAUDE.md §6 STOP: önce düzelt) | `scripts/hooks/post_validate.py` |
| **UserPromptSubmit** | güçlü SAP anahtar kelimesi (CDS/RAP/DTEL/ZSDxxx/transport...) | sap-abap-dev skill rehber nudge'ı enjekte (gap-analysis #9) | `scripts/hooks/skill_injector.py` |
| **PreToolUse** (`Bash\|mcp__sap-adt__*`) | her Bash/SAP-MCP çağrısı | transport release/create + package create deseni → **exit 2 blok** (ADR 0005-C 2. katman) | `scripts/hooks/pre_tool_guard.py` |
| **PostToolUse** (`mcp__sap-adt__*`) | SAP MCP tool sonucu | hata/guardrail/aktivasyon-fail → **patinaj kesici** hatırlatma enjekte (ADR 0006/T10) | `scripts/hooks/post_tool_failure.py` |
| **PreCompact** | context compaction öncesi | SESSION_NOTES/memory flush hatırlatması (uzun oturum güvenliği) | `scripts/hooks/pre_compact.py` |

> Yeni hook eklenirse: script'i `scripts/hooks/`'a yaz → manuel stdin testi → `settings.json` `hooks` bloğuna ekle → bu tabloya satır.

---

## 5. VS CODE EKLENTİLERİ

Editör tarafı (Claude'un yanında): UI5 Language Assistant, Fiori Tools (XML/i18n),
Pylance, ESLint, GitLens, XML/YAML. Kurulum + gerekçe + ⛔ "ABAP doğrudan-edit eklentisi
kurulmaz" kuralı: [`vscode-setup.md`](vscode-setup.md). Öneri listesi: `.vscode/extensions.json`.

---

## 6. ADOPTED TOOLING — provenance kataloğu (kaynak → ne aldık → nerede)

> **Tek doğruluk kaynağı:** dışarıdan araştırıp **aldığımız/aktive ettiğimiz** (kurduğumuz VEYA deseninden kendi yazdığımız) her şey. Keşif → kıyas → adoption metodu: `governance/research/sap-ai-tooling-comparison.md` *(proje reposunda)*. Yeni araç ararken §🔎 (marianfoo katalog). **Yeni bir şey kurunca/aktive edince bu tabloya satır.**

| Öğe | Kaynak (repo/URL) | Ne aldık | Bizde nerede | Durum |
|---|---|---|---|---|
| **sap_adt MCP** | özgün (ilham: abap-adt-api ekosistemi) | 18 ADT tool + ADR 0005/0010 server-side guardrail | `mcp_servers/sap_adt/` | ✅ aktif |
| **ui5** (MCP+2 skill) | UI5/mcp-server (resmi) | proje/validate, API-ref, ui5-linter, best-practice skill'leri | plugin + `standards/03` | ✅ aktif |
| **playwright** | @playwright/mcp (Microsoft) | tarayıcı e2e/doğrulama | plugin + `/verify`,`/run` | ✅ aktif |
| **pyright-lsp** | pyright | Python diagnostics | LSP | ✅ aktif |
| **released-object check** | ClementRingot deseni + **SAP/abap-atc-cr-cv-s4hc** JSON | tablo→released CDS successor (otoriter, 261 tablo) | `check_released_objects.py` + `reference/released_successors.json` + `refresh_released_successors.py` | ✅ aktif (reviewer WARNING) |
| **abaplint** | arc-1 deseni + `@abaplint/cli` | tuned ABAP lint (class_push gap) | `scripts/abaplint/abaplint.json` + `check_abaplint.py` | ✅ aktif (reviewer WARNING) |
| **RAP BOTD test + troubleshoot** | weiserman/rap-skills | BOTD unit-test pattern + troubleshoot tablosu | `playbook/checklists/rap-troubleshoot.md` | ✅ aktif (rehber) |
| **ATC no-suppress** | matt1as/claude-abap-skills | suppress-yasak + kategori-grupla disiplini | rap-troubleshoot §3 + `feedback_atc-priority-1` | ✅ aktif |
| **CDS-perf kuralları** | secondsky/sap-skills | CompareFilter, join-on-demand, HAVING | `standards/05` §9X | ✅ aktif |
| **Mermaid CLI** (`mmdc`) | @mermaid-js/mermaid-cli | diyagram-as-code (akış/sequence/ER/state) → SVG/PNG; FS/TS/KD görseli | `scripts/doc_tools.py` + `build_kd_pdf.py` (```mermaid fence render) | ✅ aktif (2026-06-14) |
| **Marp CLI** (`marp`) | @marp-team/marp-cli | Markdown → eğitim slaytı (PDF/PPTX/HTML) | `scripts/doc_tools.py::marp_build` | ✅ aktif (2026-06-14) |
| **alan-tablosu üreteci** | özgün | CDS(+iface+bdef+ref_docs csv) → TS§4.5/KD§6 alan tablosu (OCR DEĞİL, metadata) | `scripts/gen_field_table.py` | ✅ aktif (2026-06-14) |
| **araç keşif kataloğu** | marianfoo/sap-ai-mcp-servers | "ilk buraya bak" recall | §🔎 + skill + deferred-triggers | ✅ aktif |
| docs-MCP | marianfoo/mcp-sap-docs | doc-lookup (harici server) | — | ⏳ deferred (#15) |
| sapcli | jfilak/sapcli | RAP BOTD test-runner (`aunit --output junit4`) | — | ⏳ deferred (test gelince) |
| ai-skills-library | SAP (resmi) | sap-fiori-guidelines (tek skill) | — | ⚪ izle |

> **Template (T12):** Bu katalog + adoption metodolojisi **genericize edilip template repo'ya** taşınmalı (gelecek projeler küratörlü araç setini + "kıyasla, var/yok değil" yöntemini miras alsın). *(EMEKLİ — canlı-çekirdek mimarisinde [ADR 0020] port süreci YOK: katalog zaten core'da yaşar; genericize'ı pre-commit gate korur.)*
