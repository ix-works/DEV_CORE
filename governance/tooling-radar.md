---
type: tooling-radar
title: Genel Agent-Dev Tooling Radar (SAP-dışı dahil)
status: active
cadence-days: 21
last-run: 2026-06-13
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
| 2026-06-13 | radar ilk run ⚠️ tek-subagent (sonradan paralel'e revize edildi) | **ADOPT:** (1) `ast-grep` CLI — AST yapısal arama/refactor (ripgrep↔pyright arası eksik katman, Python+JS); (2) skill frontmatter `disallowed-tools` — ADR 0005'e ~0-maliyet proaktif 2. guardrail; (3) "CLI-over-MCP" karar-kuralı (MCP ~35-43x token) → tooling-plugins §3'e yaz. **İZLE:** Dynamic Workflows (repo-audit pilotu), PostToolUse `updatedToolOutput` (çıktı-kısaltma), `/reload-skills`. **ATLA:** CodeGraph/graf-indeks (repo ölçeği haklı çıkarmıyor), agent-browser (playwright-cli zaten lider) | ✅ **ast-grep** kuruldu + recall (skill_injector `_STRUCTURAL`) + team_setup + AGENTS/tooling-plugins; **CLI-over-MCP** ilkesi ast-grep entry'sine işlendi. ❌ **disallowed-tools DÜŞÜRÜLDÜ** (claude-code-guide doğrulaması): tool-seviyesi blacklist param-seviyesi ADR 0005 riskine UYMUYOR — asıl koruma zaten `pre_tool_guard` hook'unda (doğru katman). "Doğrula-sonra-adopt" disiplini çalıştı. |
