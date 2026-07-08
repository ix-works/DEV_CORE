---
adr: 0011
title: Veri-Çıkarma / PII (KVKK) Guard — QA/PRD'de Hassas Veri Koruması
status: accepted
date: 2026-06-02
priority: YÜKSEK
deciders: <SAP_USER>
supersedes: —
superseded-by: —
---

# ADR 0011 — Veri-Çıkarma / PII (KVKK) Guard

> Kaynak: SuperClaude-for-SAP gap analizi (`governance/research/sc4sap-gap-analysis.md` #2 — proje reposunda).
> ADR 0005'in **veri ekseni** kardeşi: 0005 obje/state korur, 0011 hassas **veriyi** korur.

## Bağlam

ADR 0005 obje/state koruyor ama canlı sistemden **kişisel/hassas veri OKUMAYI** hiç
sınırlamıyordu. Canlı (QA/PRD) sistemde bir AI ajanının müşteri (KNA1), çalışan/bordro (PA*),
banka (BNKA/IBAN), vergi no (TCKN/VKN) gibi veriyi log'a/transcript'e çekmesi **KVKK riski**.

## Karar

1. **Tier-gated (kullanıcı kararı 2026-06-02):** Guard **yalnızca QA/PRD** tier'larında aktif.
   **DEV muaf** (test/geliştirme verisi).
2. **`data_guard.require_data_access(tier, table, fields, acknowledge_risk, approval_text)`:**
   - DEV → no-op.
   - QA/PRD + hassas hedef değilse → serbest.
   - QA/PRD + hassas hedef (regex: KNA1/LFA1/ADRC/PA*/BSEG/BKPF/ACDOCA/banka/TCKN/IBAN…) →
     **açık onay** (`acknowledge_risk=True` + affirmative kelime: `onay`/`approve`/`proceed`/
     `confirmed`) yoksa **reddet**. Muğlak ifade ("dene", "çek") yetmez (sc4sap deseni).
3. **Bağlanma noktası:** Bir veri-okuma aracı (ileride `adt_table_read` / GetTableContents,
   gap-analysis #10) bu guard'dan geçer. **Şu an MCP'de doğrudan tablo-verisi çekme aracı YOK**
   → guard hazır bekler; tool eklenince devreye girer.

## Sonuç

- KVKK/veri-koruma boşluğu kapandı; canlı sistemde proaktif.
- DEV iş akışı hiç etkilenmez (muaf).
- ADR 0010 (tier) ile bağımlı: tier `_conn.get_active_tier()` ile okunur.

## İlgili
- [`0005`](0005-sap-standart-obje-koruma-ve-sistem-state-yasaklari.md) · [`0010`](0010-tier-bazli-readonly-guard.md)
- Kod: `mcp_servers/sap_adt/data_guard.py`
