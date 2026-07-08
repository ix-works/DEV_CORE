---
applies_to: [s4_private]
---
# Checklist — DDIC Domain / Data Element (DTEL) Oluşturma

> **Pre-flight.** Yeni domain/DTEL yaratmadan önce geçilir. Reviewer task'ı: `dtel_update`
> (+ `domain_creation_csv`) + `check_reuse_gate.py` (WARNING). Bu checklist kör noktaları kapatır.
>
> **Standart:** [`../../standards/01-naming.md`](../../standards/01-naming.md) §5B ·
> **Pattern:** [`../adt-domain-dtel.md`](../adt-domain-dtel.md)

---

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| DE-REUSE-01 | **Reuse-first:** önce released **standart DE** var mı? (Clean Core) Varsa onu kullan, yeni yaratma | BLOCKER | std 01 §5B / #3 |
| DE-REUSE-02 | Aynı işi gören **mevcut Z DTEL/domain** var mı? (`adt_search_objects` / repo grep) Varsa reuse — duplicate yaratma | BLOCKER | §5B + `check_reuse_gate.py` |
| DE-NAM-01 | Naming: Domain `ZSD<pkg>_D_*`, Data Element `ZSD<pkg>_E_*` (std 01) | BLOCKER | std 01 |
| DE-TR-01 | **TR master:** `sap-language=TR` login + create. MCP/post-shell EN yaratır → raw REST + `masterLanguage=TR` + post-create doğrula | BLOCKER | ADR 0005-D / `feedback_mcp-post-shell-en-master-lang` |
| DE-TR-02 | DTEL **4 field label** (short/medium/long/heading) **TAM TR** doldurulur; boş bırakılmaz | BLOCKER | ADR 0005-D |
| DE-TXT-01 | Açıklama/label **spec'ten** (<LEGACY_SOURCE>/proje) — **ASLA tahmin etme** | BLOCKER | `feedback_zli-obje-text-tahmin-yasak` |
| DE-DOM-01 | Domain fixed values / value table gerekiyorsa tanımlı; data type/length doğru | WARNING | std 01 |
| DE-ACT-01 | Aktivasyon öncesi REST GET ile TR text + tip doğrulanır; sonra activate | BLOCKER | ADR 0005-D |
| DE-005 | Standart DTEL/domain'e dokunma YASAK; append field/DTEL adını AI ÖNERMEZ (kullanıcı belirler) | BLOCKER | ADR 0005-A |
