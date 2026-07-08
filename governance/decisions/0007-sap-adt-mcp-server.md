---
adr: 0007
title: SAP ADT MCP Server — Typed Tool Layer with Hardcoded Guardrails
status: accepted
date: 2026-05-14
priority: MEDIUM
deciders: <SAP_USER>
supersedes: —
superseded-by: —
---

# ADR 0007 — SAP ADT MCP Server

## Bağlam

`scripts/` klasöründe ~30 Python script var (`create_domain.py`, `create_structure.py`, `push_object.py`, `activate_object.py` vd.). Her SAP yazma işlemi şu zincirde:

```
Coordinator → Bash tool → python scripts/<x>.py --flag1 ... → REST POST → SAP
```

Her seferinde:
- Script okunur, parse edilir, argparse hatırlanır
- Output unstructured (stdout/stderr text)
- Hata yorumlanır LLM tarafından (yapılandırılmış değil)
- Yeni script eklendikçe coordinator'ın hatırlaması gereken yüzey büyür
- ADR 0005 yasakları **guideline** seviyesinde — kod gate olarak `populate_*.py` içinde, atomic `create_*.py` çağrıları için bypass yolu var

Sprint 6'da 10 struct daha + Sprint 7+ ABAP class push/method push döngüsü yaklaşıyor. Bu hacimde:
- Typed tool calling = daha az hata
- Server-side enforcement = bypass yok
- Structured output = LLM yorumu güvenilir

## Karar

**SAP ADT MCP Server kur** — coordinator'a (ben, Claude Code) typed tool olarak expose et.

### Mimari

```
Coordinator (Claude Code) → MCP stdio → mcp_servers/sap_adt/server.py
                                              ↓ (import)
                                        scripts/sap_adt_lib.py
                                              ↓ (HTTP)
                                              SAP
```

- `scripts/sap_adt_lib.py` **tek source of truth** (HTTP, auth, retry, error parse)
- MCP server ve mevcut `scripts/*.py` ikisi de aynı lib'i kullanır
- Mevcut script'ler **silinmez** — populate batch işleri (CSV → toplu yarat) için kalır
- Coordinator atomik işlerde MCP tool'larını çağırır

### Dil + Konum

- **Dil**: Python (`sap_adt_lib.py` Python, ekosistem uyumu, `mcp` SDK Python destekli)
- **Konum**: `mcp_servers/sap_adt/` — repo kökünde, çoklu MCP eklenirse organize
- **Transport**: stdio (local), MCP standart
- **Registration**: `.mcp.json` (Claude Code'un standart project-level MCP config dosyası, `claude mcp add` ile yaratılır, repo'da paylaşılır). `.claude/settings.json`'a yazılan `mcpServers` block'unu Claude Code 2.x okumuyor — `.mcp.json` zorunlu.

### Tool Listesi (v1 — 10 tool)

| Tool | Tip | Ne yapar |
|---|---|---|
| `adt_get` | Atom | Obje GET (var mı, aktif mi, source) |
| `adt_post_shell` | Atom | Boş Z obje shell yarat (henüz aktive değil) |
| `adt_push_source` | Atom | Source body push (CDS/ABAP içerik) |
| `adt_activate` | Atom | Aktivasyon |
| `adt_domain_create` | Composite | shell + push + activate + verify GET (rollback'li) |
| `adt_dtel_create` | Composite | shell + push + activate + verify GET (rollback'li) |
| `adt_struct_create` | Composite | shell + push + activate + verify GET (rollback'li) |
| `adt_search_objects` | Query | İsim/açıklama ile obje ara |
| `adt_transport_list` | Query | Transport içeriği listele |
| `adt_lock_check` | Query | Lock var mı, kim |

### Composite Davranışı — Atomik Rollback

`adt_domain_create({name, type, length, label, package, transport})`:

1. `adt_get(name)` — var mı? Varsa `already_exists` hatası
2. `adt_post_shell` — shell yarat
3. `adt_push_source` — domain content push
4. `adt_activate` — aktive et
5. `adt_get(name)` — final state verify (aktif, doğru tip/uzunluk)

**Failure handling:**
- Adım 2 fail → exit, sistemde değişiklik yok
- Adım 3 fail → `adt_delete_shell` (rollback), exit
- Adım 4 fail (aktivasyon hatası) → `adt_get` ile inactive durumda mı bak, **inactive bırak** (coordinator karar verir: düzelt+activate veya delete)
- Adım 5 fail → coordinator'a verify_failed: <neden> dön

Tüm adımlar JSON output: `{"step": "activate", "ok": true, "object_url": "...", "elapsed_ms": 234}`

### Server-Side Guardrails — Hardcoded (ADR 0005 Enforcement)

Bypass yok, kod commit etmeden değişmez. Python kodunda `_GUARDRAILS` modülünde:

| Kontrol | Reject koşulu | Hata mesajı |
|---|---|---|
| **Z/Y prefix zorunluluğu** | `adt_post_shell(name)` ile `name` Z veya Y ile başlamıyorsa | `ADR_0005_A: Standart obje yaratma yasak: {name}` |
| **TR text zorunluluğu** | Domain/DTEL/struct için label dolu değilse veya non-TR karakter (ASCII-only) içeriyorsa | `ADR_0005_D: TR text zorunlu, label boş veya non-TR: {field}` |
| **4 label dolu** | DTEL'de short/medium/long/heading'den biri boşsa | `ADR_0005_D: 4 label zorunlu, eksik: {fields}` |
| **Std obje delete** | `adt_delete` herhangi bir std obje için (Z/Y olmayan) | `ADR_0005_A: Standart obje sil yasak` |
| **Std obje update** | `adt_push_source` Z/Y olmayan bir objeye | `ADR_0005_A: Standart obje update yasak` |
| **Transport release** | Tool listesinde transport release **yok** (eklenmez) | n/a |
| **Package create** | Tool listesinde package create **yok** | n/a |

**Not — Namespace pattern'i (L4 seviyesi):** Paket-spesifik isim pattern'leri (örn. ZSD001 paketinde `ZSD001_*` zorunlu, ZMM004'te `ZMM004_*` zorunlu) MCP guardrail'a girmez. Bu kontrol **paket `.rules.md`** seviyesinde, reviewer (`run_review.py`) tarafından enforce edilir. MCP guardrail sadece **modül-agnostik** ADR 0005 yasaklarını uygular — <PROJECT_NAME> repo'sunda çalışan tüm modüller (SD, MM, FI, BC vd.) aynı MCP'yi kullanabilir.

Guardrail'lar tool çağrısı `validate()` aşamasında çalışır — REST'e gitmeden reject. Audit log'a yazar (`mcp_servers/sap_adt/audit.log`).

### Stateless mi Stateful mi?

**Stateless v1.** Her tool çağrısı bağımsız HTTP session açar (lib zaten retry + CSRF token yapıyor). Connection pooling sonraki sürümde.

### Configuration

- `.conn_adt` dosyasını `sap_adt_lib.find_conn_file()` ile bulur
- Ek MCP-spesifik config: `mcp_servers/sap_adt/config.yaml` (audit log path, request timeout)

## Gerekçe

- **Typed tool calling**: argparse string parsing yok, Pydantic/JSONSchema ile validation
- **Bypass-free guardrails**: ADR 0005 yasakları **artık tartışmasız** — server reddediyor
- **Structured output**: LLM rapor yorumlamak yerine JSON parse ediyor
- **Composite atomicity**: 3-4 atom çağrısının coordinator tarafında ezberlenmesi yerine tek tool, rollback dahil
- **Aynı lib, iki arayüz**: mevcut populate_*.py batch'leri kırılmaz, MCP atomik işlere odaklanır
- **Sprint 7+ amortize**: ABAP class/method push döngüsü için her tool 5-10 saniye tasarruf, sprint başına ~30-60 dk

## Sonuçlar

- ✅ ADR 0005 yasakları bypass-free
- ✅ Coordinator'ın 30 script ezberleme yükü → 10 typed tool
- ✅ Composite'lerde rollback otomatik (manuel temizlik düşer)
- ✅ Structured output → LLM yorum hatası düşer
- ❌ Bir kerelik kurma yatırımı ~1 gün (server + 10 tool + test)
- ❌ Yeni obje tipi eklemek = MCP tool ekleme + script ekleme (çift bakım — mitigation: lib paylaşımı)
- ❌ MCP SDK Python dependency (mcp paketi)

## Reviewer ile İlişki (ADR 0006)

Reviewer **MCP composite tool ve adt_push_source içine entegre.** Coordinator manuel `run_review.py` çağırmaz — tool çağrısı içinde otomatik 0. adım çalışır:

```
adt_struct_create(..., artifact_path='ERP/.../X.asddls')
  → 0. reviewer (otomatik, scripts/validators/run_review.py --json)
       BLOCKER → tool reject (SAP'a hiç gitmez)
       WARNING → devam + response'a reviewer field'ı
       PASS    → devam
  → 1. MCP guardrails (ADR 0005)
  → 2. create + activate + verify
```

Manuel CLI **paralel kalır** ama coordinator akışında kullanılmaz:
- Lokal-only draft kontrolü için
- Yeni validator geliştirirken test için
- CI/pre-commit hook (gelecekte) için

`adt_push_source` her zaman reviewer çağırır (object_type'tan task çıkararak). `skip_reviewer=True` flag var, acil durum dışında kullanılmaz.

**Üç katman:** Reviewer (lokal kalite) + MCP guardrail (REST parametre) + SAP validasyonu. Birbirinin yerine geçmez, kaçırırsa diğer yakalar.

## Mevcut Script'lerle İlişki

| Script tipi | MCP'ye geçer mi | Sebep |
|---|---|---|
| `create_<x>.py` (atomik yarat) | ❌ MCP composite çağrılır | Tek nokta |
| `populate_<x>.py` (CSV → batch) | ✅ Kalır | Batch işler, CSV-driven, audit önemli |
| `activate_object.py` | ❌ MCP `adt_activate` | Tek nokta |
| `push_object.py` | ❌ MCP `adt_push_source` | Tek nokta |
| `download_object.py`, `get_*` | ✅ Kalır (read-only ad-hoc) | MCP'ye paralel, ad-hoc CLI kullanım için |
| `sprint_*.py`, `td_spec_check.py` | ✅ Kalır | Validator/gate, MCP'den önce çalışır |

Coordinator script ile mi MCP ile mi çalışacağına kararı:
- **Tek obje yaratım** → MCP
- **CSV'den toplu yaratım** → populate_*.py
- **Pre-flight check / validator** → script
- **Aktivasyon, push** → MCP

## Sprint 6 Pilot

Kalan 10 struct yaratımı MCP ile:
1. `sprint6_adapt_struct.py` ile lokal `.ddls.asddls` üret (<LEGACY_SOURCE> source → Z prefix adapt)
2. `run_review.py` → PASS
3. `adt_struct_create(...)` → composite, atomic
4. Verify

**Başarı kriteri:** 10 struct'ın ≥9'u tek seferde aktif (≥%90). Rollback olursa hatayı incele → guardrail/composite logic'i düzelt.

## İlgili

- [`0003-layered-rule-architecture.md`](0003-layered-rule-architecture.md) — L1-L4 + kod gate katmanları
- [`0005-sap-standart-obje-koruma-ve-sistem-state-yasaklari.md`](0005-sap-standart-obje-koruma-ve-sistem-state-yasaklari.md) — Guardrail kaynak yasaklar
- [`0006-reviewer-agent-pattern.md`](0006-reviewer-agent-pattern.md) — Pre-flight kalite; MCP guardrail tamamlayıcı
- [`../../scripts/sap_adt_lib.py`](../../scripts/sap_adt_lib.py) — Paylaşılan HTTP/auth katmanı
- [`../../mcp_servers/sap_adt/`](../../mcp_servers/sap_adt/) — Server implementasyonu
