---
name: intake-triage
description: >
  Runs the INTAKE TRIAGE protocol BEFORE any build starts: classify scope (S0 point-fix /
  S1 localized / S2 comprehensive), identify module + work-type, extract domain topics from
  the requirements, research three axes (domain knowledge; the live system + related code for
  reuse and blast-radius; prior-art in memory/playbook), then evaluate with evidence. Prevents
  guess-driven building and missed reuse. Use when the user requests any new development,
  feature, report, field, column, screen change, revision, modification, fix, or enhancement,
  or when requirements arrive via prompt, Excel, or a functional spec (FS). Fires on
  paraphrased requests a keyword hook would miss. Triggers include "bu ekrana kolon koyalım",
  "rapora şu alanı getir", "şunu da ekleyelim", "yeni rapor lazım", "şu alan yanlış geliyor",
  "revize edelim", "FS geldi". DO NOT USE FOR: pure research or code-reading questions, this
  repo's own tooling/methodology changes (hooks, validators, CI, CLAUDE.md), documentation-only
  work, or a request already triaged in this session (do not re-run the protocol).
---

# INTAKE TRIAGE — geliştirme talebi alım protokolü (native keşif)

> ⚠ **Compaction notu:** Skill gövdesi kırpılırsa BAŞI korunur — özü burada:
> **KAPSAM sınıfla → modül belirle → isterlerden konu çıkar → 3 eksen araştır → KANITLI
> değerlendir.** Hafıza=hipotez, canlı sistem=otorite. **TAHMİN YASAK.**

> Bu skill, bir **geliştirme/revizyon/rapor/alan/ekran talebini** SEMANTİK olarak tanır
> (keyword-hook'un kaçırdığı parafraze ifadeleri de: "bu ekrana kolon koyalım", "rapora
> müşteri adını getir"). Tetiklendiğinde ITG protokolünü uygula.

## Protokol (tam metin: `core/playbook/intake-triage.md`)

1. **KAPSAM sınıfla** — S0 nokta-düzeltme / S1 lokalize / S2 kapsamlı — ve GEREKÇESİNİ yaz.
2. **Modül + iş-tipini belirle**; modül kural-paketi varsa (`core/playbook/modules/<kod>.md`) OKU.
3. **İsterlerden konu çıkar** — her anlamlı alan/gereksinim hangi domain-konusunu tetikliyor
   (ör. "kullanılabilir stok" → availability check/ATP).
4. **3-EKSEN araştır:** (a) domain bilgisi (docs-MCP/resmi kaynak) · (b) CANLI sistem + ilişkili
   kod (`adt_where_used`/`adt_package_contents`/`adt_get` — reuse + blast-radius) · (c) kurumsal
   hafıza/prior-art (memory + playbook + SESSION_NOTES). Z-obje hatırlanıyorsa CANLI DOĞRULA
   (hafıza=hipotez, canlı=otorite; ADR 0016). **TAHMİN YASAK.**
5. **KANITLI değerlendir** — reuse + mevcutla tutarlılık + geçmiş-ders + risk.
6. **Kapsam-orantılı aksiyon:** S0 hafif geç (soru/artefakt yok) · S1 hedefli soru · S2 tam
   zincir → intake-artefaktı + EARS/INVEST DoR + MUTABAKAT, sonra build.

> **Not (redizayn 2026-07-10):** ITG keşfi eskiden yalnız `intake_triage.py` prompt-keyword
> regex'iyle yapılıyordu — kırılgandı (keyword-seti dışı talepler ITG'yi HİÇ tetiklemiyordu,
> 5/5 kaçış ölçüldü). Artık üç katman: (1) bu native skill (semantik keşif), (2) regex hook
> (erken hatırlatma), (3) `itg_backstop.py` (SAP-tool sınırında deterministik net). S2 sign-off
> gate'i `check_itg_signoff` değişmedi.
