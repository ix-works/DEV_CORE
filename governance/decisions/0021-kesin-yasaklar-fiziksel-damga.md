# ADR 0021 — KESİN YASAKLAR: fiziksel damga + drift-guard (import'a bağlı değil)

**Durum:** Kabul edildi (2026-07-08, kullanıcı direktifi)
**Bağlam ADR'leri:** [0005](0005-sap-standart-obje-koruma-ve-sistem-state-yasaklari.md) (yasakların kendisi) · [0019](0019-kural-enforcement-mimarisi-3-eksen-coverage-check.md) (enforcement mimarisi) · [0020](0020-canli-cekirdek-junction-mimarisi.md) (canlı-çekirdek + junction)

## Sorun

Canlı-çekirdek mimarisinde (ADR 0020) proje `CLAUDE.md`'si ince: metodolojiyi
`@core/CLAUDE.core.md` **import'uyla** yükler. KESİN YASAKLAR metni (ADR 0005: A/B/C/D +
"TAHMİN YASAK = kanıtlı hareket et") core'da yaşıyordu ve projeye **yalnızca bu import**
üzerinden geliyordu.

İki enforcement modu ayrışır:
- **Araç-seviyesi** (SAP objesine dokunma, transport yaratma): `pre_tool_guard` + MCP
  server guardrail'leri koruyor; junction kopuksa shim tool'u exit-1 ile bloklar, MCP
  server yüklenmez → SAP-yazma imkânsız (gürültülü, güvenli).
- **Talimat-seviyesi** (modelin A/B/C/D'yi planlarken *anlaması* + saf davranışsal
  "tahmin etme"): yalnızca import'la geliyor → **junction kırılırsa sessizce context'ten
  kaybolur.** Kod-yedeği yok.

Kullanıcı bunu risk olarak işaretledi: *"link/referans ile taşımak riskli; yasaklar her
projede fiziksel kural olarak set edilmeli."* Haklı — okunabilir anayasa tek indirekt
referansa asılıydı.

## Karar

Yasaklar bloğu her projenin **kök `CLAUDE.md`'sine FİZİKSEL damgalanır.** Kök CLAUDE.md
Claude Code tarafından junction'sız **doğrudan** yüklenir → junction kırılsa da anayasa
context'te. "Kopya yok" ilkesini (ADR 0020) bilinçli deler; anayasal güvenlik için değer.
Drift, tek-kaynak + guard ile önlenir:

1. **Tek kanonik kaynak:** `claude/kesin-yasaklar.canonical.md` (ML-agnostik; tek gerçek).
2. **Fiziksel damga:** `init_project` bloğu kök CLAUDE.md'ye `<!-- KESIN-YASAKLAR:BEGIN/END -->`
   arasına yazar; `@import` sonra gelir. `CLAUDE.core.md` inline bloğu → kanoniğe-işaret +
   özet (çifte-yükleme yok).
3. **Drift-guard** (`check_kesin_yasaklar.py`, BLOCKER): damga == kanonik mi? Bağlı olduğu
   yerler: `run_all_validators` (HARD) · `session_start` (yüksek-sesli uyarı) ·
   `pre_tool_guard` (**SAP-yazma öncesi hard-blok** — junction sağlamken damga
   silinmiş/bozulmuş → yasaklar context'te yok → yazma reddedilir; junction-kopuk zaten
   shim'de yakalanır).
4. **Yeniden-damga:** `sync_yasaklar.py` kanonik değişince (nadir) tüm projeleri damgalar;
   guard damgalanmayanı yakalar.

## Sonuç

- Yasaklar her projede fiziksel var (junction'dan bağımsız) + tek kaynak (drift yok) +
  guard-zorlamalı (garanti). Kullanıcı gereksinimi ("her projede mutlaka uygulanacak")
  kod-seviyesinde karşılanır.
- Maliyet: kök CLAUDE.md'de ~20 satır damga (en önemli 20 satır) + kanonik değişince
  `sync_yasaklar` koşma yükü (nadir; ADR 0005 anayasal, neredeyse hiç değişmez).
- Yeni proje: `init_project` otomatik damgalar. Mevcut proje: `sync_yasaklar.py`.

## Alternatifler (reddedildi)

- **Yalnız import (mevcut):** kullanıcı reddetti — tek indirekt referans, sessiz kayıp.
- **Yalnız managed-policy (D33):** araç-seviyesini kapar ama talimat-seviyesi anayasayı
  context'e koymaz.
- **CLAUDE.core.md @import zinciri (nested):** hâlâ junction'a bağlı; fiziksel değil.
