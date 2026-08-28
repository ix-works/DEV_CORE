---
type: tooling-radar
title: Genel Agent-Dev Tooling Radar (SAP-dışı dahil)
status: active
cadence-days: 21
last-run: 2026-08-28
---

# Genel Agent-Dev Tooling Radar

> **Neden var (kök sorun).** Tooling-incelemelerimiz uzun süre **SAP-AI-dar** kaldı
> (`governance/research/sc4sap-gap-analysis.md` — proje reposunda → SAP-AI katalogları).
> Genel "agent geliştirme verimliliği" alanı (vision-loop maliyeti, MCP↔CLI token farkı,
> tarayıcı/araştırma araçları) **taranmıyordu** → `playwright-cli` gibi büyük verim-kazançları
> kullanıcı sorana kadar yüzeye çıkmadı (2026-06-13 dersi). Bu radar o körlüğü kapatır:
> **periyodik, SAP-dışını da kapsayan, proaktif** bir tarama.

## Nasıl çalışır (mekanizma)

| Soru | Karar | Gerekçe |
|---|---|---|
| **Çalıştıran** | **PARALEL fan-out: kategori başına 1 subagent (6) + 1 sentez** | her kategori bağımsız → seri tek-subagent dikkati böler/yavaş; paralel = hızlı + kategori-derinliği. Tek subagent ANTİ-PATTERN (ilk run'da yapıldı, düzeltildi 2026-06-13) |
| **Ne zaman** | **Açılışta (SessionStart) bayatlık-kontrolü** | çalışırken=dağıtıcı; kapanışta=güvenilmez (oturum aniden biter); açılışta ucuz tarih kontrolü |
| **Sıklık** | `cadence-days: 21` geçince **nudge** (her oturum DEĞİL) | araç-manzarası hızlı ama saatlik değil; gürültü olmasın |
| **Tetik dosyası** | `scripts/hooks/tooling_radar_check.py` | `last-run` bayatsa 1-satır hatırlatma enjekte eder; değilse SESSİZ |
| **Cadence paylaşımı** | repo'daki `last-run` (team-shared) | biri çalıştırınca herkes için sıfırlanır |

**Akış:** açılışta bayatsa → hook nudge atar → AI **aktif işi bölmeden**, iş-arası uygun anda
kullanıcıya önerir/çalıştırır → subagent tarar → bulgular aşağıdaki log'a + adopt-adayları
[`tooling-plugins.md`](tooling-plugins.md)'ye → bu dosyada `last-run` bugüne güncellenir.

## Kapsam (SADECE SAP-AI DEĞİL)

Her turda şu kategorilerde "yeni/değişen + bizi zenginleştirir mi" taranır:
1. **Tarayıcı/UI doğrulama** — playwright varyantları, agent-browser, vision-vs-snapshot/CLI, bounding-box assert.
2. **Token-verimlilik / MCP↔CLI** — MCP yerine CLI+skills kaymaları, snapshot-to-disk, context-tasarruf desenleri.
3. **Arama/retrieval** — kod arama, semantic/grep hibrit, repo-haritalama.
4. **Orkestrasyon** — subagent/workflow desenleri, paralel fan-out, judge/verify patternleri.
5. **Kod-zekası** — LSP/lint/type entegrasyonları, API-reference (tahmin-kesici) araçlar.
6. **Claude Code ekosistemi** — yeni skill/plugin/hook yetenekleri, settings özellikleri.

> SAP-AI özel taraması AYRI kalır (sc4sap gap + tooling-plugins §🔎 recall). Bu radar onun
> **tamamlayıcısı** — genel agent-dev tarafı.

## Çalıştırma — PARALEL fan-out (ZORUNLU desen)

Ana AI radar'ı tetiklerken **tek subagent koşmaz** (anti-pattern). Bunun yerine:

**Faz 1 — 6 kategori-subagent PARALEL** (tek mesajda 6 Agent çağrısı): her biri AŞAĞIDAKİ şablonla,
yalnız KENDİ kategorisini derinlemesine tarar (structured çıktı döner; ana context'e kısa).

```
Sen "<KATEGORİ>" kategorisinde bir agent-dev verimlilik aracı tarayıcısısın (güncel: Haziran 2026).
1. 3-4 WebSearch yap: "<KATEGORİ> AI coding agent tooling 2026", ilgili spesifik sorgular; oku (WebFetch).
2. Bizim MEVCUT stack'i oku: governance/tooling-plugins.md + .claude/skills/ (klasör) + vscode-setup.md.
   Zaten var: SAP ADT MCP, ui5-mcp, playwright MCP + playwright-cli, pyright-lsp, subagent/Workflow.
3. KIYAS (var/yok DEĞİL): "bizdeki X vs bu aday — gerçekten zenginleştirir mi? maliyet?". Bizde olanı/marjinali ELE.
KANIT KURALLARI: TAHMİN YASAK; bulamadığını "yeni değer yok" diye açıkça yaz.
ÇIKTI (final mesaj SADECE bu): her aday için → **araç** | ne yapar | bizi-nasıl-zenginleştirir |
adopt-maliyeti (düşük/orta/yüksek) | öneri ADOPT/İZLE/ATLA | kaynak-URL. Maks 3-4 yüksek-değer.
```
Kategoriler: 1.Tarayıcı/UI-doğrulama · 2.Token-verim/MCP↔CLI · 3.Arama/retrieval · 4.Orkestrasyon ·
5.Kod-zekası(LSP/lint/API-ref) · 6.Claude Code ekosistemi(skill/plugin/hook/SDK).

**Faz 2 — sentez** (ana AI veya 1 sentez-subagent): 6 çıktıyı birleştir, dedup, çapraz-kategori kıyas,
top ADOPT'ları sırala → "Bulgu Log"a satır + ADOPT'ları tooling-plugins.md'ye aday-satır.
Otomatik kurulum YAPMA — kullanıcı onayı sonrası. Bitince frontmatter `last-run`'ı bugüne güncelle.

## Bulgu Log

| Tarih | Tarayan | Yüksek-değer bulgular | Adopt edilen |
|---|---|---|---|
| 2026-06-13 | (manuel, kullanıcı tetikledi) | `playwright-cli` (tarayıcı/UI; MCP'den ~4x az token, snapshot→disk) + bounding-box-assert deseni | ✅ playwright-cli + token-verimli akış (commit efb58de8/bd82dcb) — radar bu eksiklikten doğdu |
| 2026-07-08 | HEDEFLİ SAP-AI turu (kullanıcı 17-repo listesi; 4 paralel paket: ADT-MCP'ler / ADT-API+editör / skills / docs-MCP) — genel 6-kategori turu KAPSANMADI (bir sonraki radar genel-odaklı koşulmalı) | **ADOPT-ADAY (onay bekliyor, tooling-plugins §6):** (1) MCP **runtime-teşhis paketi** — ST22 dump + ABAP-Unit koşucu + versiyon-diff + guarded-SQL + scope-grep (yzonur kanıtlı endpoint'ler + abap-adt-api haritası); (2) yazma **audit-JSONL** + QA/PRD readOnly-default; (3) ATC package/transport scope; (4) adt_get satır-aralığı; (5) **mcp-sap-docs** pilotu (resmi ABAP keyword-docs); (6) released_successors kapsam genişletme (DDLS/DTEL/BDEF + full-state — ROSA fikri); (7) pre_tool_guard npx-sürüm-pin + credential-scan; (8) 4 mikro checklist/standards eklemesi. **İZLE:** SAP RESMÎ ADT MCP (custom-server emeklilik sorusu, çeyreklik) · ADT debugger fizibilite · arc-1 SAPDiagnose · sc4sap görüntü-spec pipeline (docs-tetikli) · ui5lint FE-gate · refactor-guardrail playbook · cross-system diff. **ATLA:** fr0ster/babamba2 tool-enflasyonu · ROSA server · mario salt-GET. Karşı-tespit: governance-guardrail + composite+readback + SRVB-publish sınıflarında 17 repo içinde rakipsiziz. | (onay sonrası) |
| 2026-07-26 | **HEDEFLİ referans-repo kontrolü** (kullanıcı tetikledi; §6 provenance kataloğundaki 20 repo `gh api` ile canlı okundu) — ⚠ **genel 6-kategori radar turu DEĞİL, `last-run` SIFIRLANMADI** (07-08 turu geçerli; cadence bozulmasın) | **BİZDE KIRIK (2):** (1) `released_successors.json` **hiç üretilmemiş** → `check_released_objects` boş harita ile sessiz PASS (fail-open); kök sebep `refresh_released_successors.py` çıktı klasörünü yaratmıyor → tek satır fix + harita üretildi (261 tablo). (2) `@abaplint/cli` **pin'siz** (`npx --yes`) → her koşumda upstream latest; 07-08'den beri 43 commit. **UPSTREAM:** yzonur/sap-adt-mcp 0.8.56 (ABAP **debugger** faz 1-3 + crash/500 guard'ları) · mcp-sap-docs v0.3.52 (Fiori RAG + retrieval eval harness) · UI5/mcp-server 0.2.16 & @playwright/mcp 0.0.78 (plugin katmanı oto-güncel, aksiyon yok) · sapcli/ROSA/superclaude aktif ama tetiksiz · kts982 07-08'den beri 0 commit (blokaj Basis ön-koşulunda) · weiserman/matt1as/abap-adt-api durgun. **KATALOG HATASI:** `secondsky/sapui5-linter` + `secondsky/sap-dependency-security` ayrı repo değil (404) → `secondsky/sap-skills` monorepo `plugins/` alt-klasörü | ✅ successors harita + mkdir fix · ✅ abaplint pin 2.120.5 · ✅ katalog düzeltmesi · ✅ lessons-learned PATTERN #14 (devreye-alma) — debugger/docs-MCP ADAY olarak bekliyor |
| 2026-08-28 | **6-kategori PARALEL fan-out (sonnet) + HEDEFLİ referans-repo turu** — kullanıcı tetikledi; 7 ajan tek mesajda, lider her yüksek-değer iddiayı BAĞIMSIZ yeniden ölçtü | **⛔ ASIL DEĞER — DEFTER BAYATLIĞI (5, hepsi ölçüldü; dış araçta değil BİZDE):** (1) **`Q105 ③` kuyrukta `AÇIK` ama İŞ BİTMİŞ** — `run_review.py:271-386` `_GATE_DURUM_RE` ile `IX-GATE-STATUS`'ü TÜKETİYOR (`rc==0 && measured=false` → `PASS` değil **`SKIP`**), getiren commit `6e4a1ec` (PR #165); fixture `tests/fixtures/reviewer_skip_sozlesmesi/run.py` **21/21 OK**, `V10` tam bu ekseni ölçüyor. Kaydın kanıtı core HEAD `4b15dc1` (PR #164) üzerinde ölçülmüştü ⇒ **kanıt bayat, hüküm değil**. (2) **`Q166`** regex fix'i de `main`'de (`check_standard_table_fields.py:87-91` `INCLUDE_LINE` **(b) dalı** → `include <ad> not null;`, yine `6e4a1ec`) — ⚠ uçtan uca `KNA1` teyidi koşulmadı. (3) **U1 JIT-recall §6'da `⏳ ADAY` ama CANLI** — `scripts/hooks/recall_inject.py` + `settings.json` UserPromptSubmit; ⚠ mekanizma **FTS5/BM25 DEĞİL** (dosyada 0 eşleşme), **ağırlıklı token-kesişimi** (ESIK=5, top-3, fail-open). Katalog iki yönden yanlıştı: statü + mekanizma. (4) **`defer_loading`/Tool Search aktif ama §6'da provenance satırı YOK** (T9 açık kalem) — bu oturumun kendi tool-listesi kanıt. (5) **route-BFS + `grayscaleDiff64` helper'ı YAZILMIŞ** (`scripts/ui-smoke/helpers.ts` + selftest) ama gerçek smoke spec'ine **kablolanmamış** — `⏳ ADAY` etiketi bunu göstermiyordu. **BAYAT/DRIFT (referans-repo turu):** `@abaplint/cli` pin **2.120.5 → npm latest 2.120.38 = 33 sürüm / 91 commit geride**; lider hakemledi (iki ajan çelişti): blog/CHANGELOG'da **duyuru yok** ama commit günlüğünde **var** — `cds_naming namespaced prefix (#4244)` · `CDS syntax checks (#4223)` · `cloud_types SMBC/TOBJ/G4BA (#4231)` · `CLASS_CONSTRUCTOR public section (#4217)` ⇒ *duyuru yok ≠ ilgili değişiklik yok*, **enstrüman farkı**. `released_successors.json` **İKİ kopya** (payload aynı, `_meta.generated` 2026-07-26 vs **2026-06-09**); otoriter olan core'daki (`DATA_PATH = parents[2]`), proje-lokal kopyaya **kod referansı 0** (PATTERN #26 gereği ölçüldü, silinmedi — öneri). `sap-gui` satırındaki karantina yolu `C:\IX\_intake\...` **artık YOK** (paket site-packages'ta, v0.2.2 = latest). `marianfoo/arc-1` → **`arc-mcp/arc-1`** (sahip değişti). **UPSTREAM:** `yzonur/sap-adt-mcp` 0.8.56→**0.8.58** (debugger/audit-JSONL ADAY'larımızın kaynağı olgunlaşıyor) · `mcp-sap-docs` v0.3.53 (heap-exhaustion fix) · `secondsky/sap-skills` 426★ çok aktif, iki alt-plugin yerinde · `vscode_abap_remote_fs` kendini artık *"Agentic AI Platform"* diye tanımlıyor · `weiserman/rap-skills` **donuk** (tek commit, 2026-02-24) · ui5-mcp 0.2.18 + playwright-mcp 0.0.79 = **latest, gecikme yok** · ⚠ **brif çürütüldü:** `SAP/abap-atc-cr-cv-s4hc` push aldı diye successors verimiz bayat SANILDI — beslediğimiz `objectReleaseInfo_PCELatest.json` **2026-02-25'ten beri değişmedi** ⇒ refresh **tetiksiz**. **ADOPT-ADAY (onay bekler):** ① playwright `--hires`/`scale:"device"` (yoğun ALV grid netliği, ~0 maliyet) ② abaplint pin bump + yan-yana koşum ③ CC **2.1.198+ model-miras** ölçümü (bizim *"sap-research→haiku indirilebilir"* kuralı sessizce geçersiz olabilir; sürümümüz **2.1.250**). **İZLE:** `updatedToolOutput` **GA** (PostToolUse, artık tüm tool'lar; `updatedMCPToolOutput` deprecated) · Vercel `agent-browser` (2026-06-13'te ATLA denmişti ama gerekçede **ölçüm yoktu** → tek-vaka turu) · `arc-1-lsp` · SAP resmî ADT MCP (**GA iddiası** — ajan raporu, bağımsız doğrulanmadı) · CLI-over-MCP **~35-43x** rakamı defer_loading ÖNCESİ olabilir (bağımsız benchmark farkı ~2-5k'ya indiriyor) → doktrini değiştirme, **ölçümü tazele**. **ATLA:** CodeGraph/repo-graph/agentmap (üçü de tree-sitter, **ABAP yok**; ABAP blast-radius'u zaten `adt_where_used`+`adt_impact_analysis` canlı karşılıyor) · Percy/Applitools SaaS · Stagehand · skills-over-MCP toptan göçü · CLAUDE.md `<60` satır trim (kendi #17204 ölçümümüz + Vercel karşı-bulgusu riskli kılıyor). **ÇÜRÜTÜLDÜ:** `paths:` frontmatter — issue **#49835** (açık, maintainer `[reproduced]`): skill *tembel tetiklenmiyor* değil **tamamen keşfedilemez** oluyor ⇒ kaçınmamız doğru, gerekçe **daha güçlü**. | ⏳ hiçbiri otomatik kurulmadı (protokol: onay sonrası) — bu turda YAPILAN: 5 bayat defter satırı düzeltildi |
| 2026-08-01 | 6-kategori PARALEL fan-out (sonnet) + 2 level-up derin-analiz (referans-repo + resmî-yetenek) — kullanıcı tetikledi; filtre: gerçek-değer+çakışmasızlık+yan-etki (kullanıcı direktifi) | **MİMARİ DOĞRULAMALARI (dış kanıt):** hub+maker-checker=2026 production-default · 3-katman arama (lexical/structural/graph) konsensüs, semantic-first REDDEDİLDİ · T-trigger closed-loop'un akademik karşılığı (arXiv 2607.13091) · CLI-over-MCP bağımsız 17x ölçümü · model-tiering (P8'imiz) wshobson/VoltAgent standardı. **ADOPT-ADAY (onay bekler):** (1) **U1 JIT-recall enjeksiyonu** — UserPromptSubmit/spawn'da lokal FTS5-BM25 top-K ders-İNDEKSİ (ajan-farkında; agent_id payload kanıtlı; mcp-sap-docs aynı taşın offline kanıtı) → "yazılıydı-okunmadı" sınıfının ilacı; (2) plan-artifact (çok-adımlı geri-alınamaz zincirde plan→dosya→onay; formalizasyon, araçsız); (3) Workflow-pilot (bug-gate döngüsünü 1 gerçek build'de Workflow-script'le kıyasla); (4) ui-smoke'a route-BFS+64×64-grayscale-diff teknikleri (bağımlılıksız); (5) ders-hijyeni 2 alan (son-doğrulama+applies_to; yalnız yeni/dokunulan derslere). **İZLE:** memory:project pilotu (aday rol: GATEWAY — bug-expert taze-context kuralıyla ÇELİŞİR, elendi) · K1 regex+haiku iki-katman guard (FP-maliyeti ölçülü ama moratoryum-ağır) · K2 Monte-Carlo tetiklenme-güvenilirliği (inspector-v3 fikri) · U2 oturum-sonu otomatik NOTES-taslağı (taslak+onay modeli şart) · U3 pattern→skill (#19 adayı) · arc-1-lsp (ABAP imza-düzeyi doğrulama; 2★ erken) · SAP resmî ABAP-MCP GA=Q2-2026 teyidi · MCP disk-persistence annotation (önce canlı-gözlem) · grepai · mem0-fikri (recency-ranking; araç local-first'le çelişir) · Shiplight. **ATLA:** Stagehand (çözdüğü sorun bizde yok+token-doktrini tersi) · SeeRepo (CORE-INDEX zaten var) · Applitools-sınıfı SaaS · handoff-loop-guard (mimari bağışık) · PreCompact-arşiv (transcript zaten kalıcı) · strict-tool-schema (pydantic zaten yapıyor) · API-yüzeyi önerileri (prompt-caching-config/context-editing/batch — CLI'da yüzey yok). **ÇÜRÜTÜLDÜ-uygulanmaz:** radar-6'nın "paths:→globs:" önerisi (canlı ölçümümüz tersi; 2026-07-10 dersi geçerli). **KAPANDI:** defer_loading zaten aktif (oturum kanıtı: sap-adt 30 tool deferred duyuruldu). | (onay sonrası) |
| 2026-06-13 | radar ilk run ⚠️ tek-subagent (sonradan paralel'e revize edildi) | **ADOPT:** (1) `ast-grep` CLI — AST yapısal arama/refactor (ripgrep↔pyright arası eksik katman, Python+JS); (2) skill frontmatter `disallowed-tools` — ADR 0005'e ~0-maliyet proaktif 2. guardrail; (3) "CLI-over-MCP" karar-kuralı (MCP ~35-43x token) → tooling-plugins §3'e yaz. **İZLE:** Dynamic Workflows (repo-audit pilotu), PostToolUse `updatedToolOutput` (çıktı-kısaltma), `/reload-skills`. **ATLA:** CodeGraph/graf-indeks (repo ölçeği haklı çıkarmıyor), agent-browser (playwright-cli zaten lider) | ✅ **ast-grep** kuruldu + recall (skill_injector `_STRUCTURAL`) + team_setup + AGENTS/tooling-plugins; **CLI-over-MCP** ilkesi ast-grep entry'sine işlendi. ❌ **disallowed-tools DÜŞÜRÜLDÜ** (claude-code-guide doğrulaması): tool-seviyesi blacklist param-seviyesi ADR 0005 riskine UYMUYOR — asıl koruma zaten `pre_tool_guard` hook'unda (doğru katman). "Doğrula-sonra-adopt" disiplini çalıştı. |
