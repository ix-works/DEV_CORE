---
adr: 0010
title: Tier-bazlı (DEV/QA/PRD) Readonly Guard + Multi-System Bağlantı
status: accepted
date: 2026-06-02
priority: YÜKSEK
deciders: <SAP_USER>
supersedes: —
superseded-by: —
---

# ADR 0010 — Tier-bazlı Readonly Guard + Multi-System Bağlantı

> Kaynak: SuperClaude-for-SAP gap analizi ([`../research/sc4sap-gap-analysis.md`](../research/sc4sap-gap-analysis.md) #1).
> İlke: **"Safety is not memory, it is code"** — tier dosyadan okunur, agent hatırlamasına bırakılmaz.

## Bağlam

ADR 0005 *neyi* (Z/Y, standart obje, transport) yazabileceğimizi sınırlıyordu ama
*hangi sisteme* yazılabileceğini değil. Tek sistem (DS4/DEV) varken bile, transport ile
QA/PRD'ye geçiş başlayınca **yanlış sisteme yazma** riski doğar (yanlışlıkla QA/PRD
bağlantısı aktifken `domain_create`/`push`/`activate`). Bu canlıda istenmeyen değişiklik =
ciddi olay.

## Karar

1. **Her bağlantıya değiştirilemez `ADT_SAP_TIER` etiketi** (DEV/QA/PRD). `.conn_adt`'de satır.
2. **Kademe matrisi:**
   | Tier | Mutasyon (create/push/activate/delete) | Okuma/analiz |
   |---|---|---|
   | DEV | ✅ serbest | serbest |
   | QA | ⛔ reddedilir | serbest (hassas veri → ADR 0011) |
   | PRD | ⛔ reddedilir | serbest (hassas veri → ADR 0011) |
3. **Server-side enforcement (ADR 0007 ile aynı felsefe):** `guardrails.require_writable_tier()`
   tüm mutasyon MCP tool'larında (atom: post_shell/push_source/activate/delete; composite:
   domain/dtel/struct create) çağrılır. Tier `_conn.get_active_tier()` ile **her çağrıda
   taze** okunur (`.conn_adt` otoriter, env fallback).
4. **Multi-system altyapısı:** `conn/<tier>.env` slotları (DEV/QA/PRD) + `conn/*.env.template`
   (commit'li örnek) + `scripts/switch_tier.py` (tier geçişi, yüksek-sesli QA/PRD uyarısı).
   Gerçek `conn/*.env` gitignore'lı.
5. **Tanı:** `scripts/sap_doctor.py` aktif tier + bağlantı sağlığını raporlar.

## Fail-safe

`ADT_SAP_TIER` absent → DEV varsayılır + görünür uyarı (mevcut/eski `.conn_adt`'ler kırılmasın).
QA/PRD koruması, o sistemlerin conn dosyalarının her zaman `ADT_SAP_TIER=QA|PRD` ile
etiketlenmesiyle sağlanır (template + switch_tier zorlar). *Backlog: fail-closed + keychain
(gap-analysis #6) PRD gelince değerlendirilecek.*

## Sonuç

- Bugün tek sistemde bile bedava sigorta; QA/PRD gelince guard hazır.
- Kullanıcı sistem bilgilerini `conn/<tier>.env`'e girer (slotlar hazır).
- ADR 0005 §C (transport/state) ile birlikte tam koruma katmanı.

## İlgili
- [`0005`](0005-sap-standart-obje-koruma-ve-sistem-state-yasaklari.md) · [`0007`](0007-sap-adt-mcp-server.md) · [`0011`](0011-veri-cikarma-pii-guard.md)
- Kod: `mcp_servers/sap_adt/{_conn.py,guardrails.py}`, `scripts/{switch_tier,sap_doctor}.py`, `conn/`
