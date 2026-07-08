# CLAUDE.md — <PROJECT_NAME> (ince proje loader'ı)

<!-- KESİN YASAKLAR bloğu init_project tarafından buraya FİZİKSEL damgalanır (junction-
     bağımsız daima yüklü). Aşağıdaki @import metodolojinin GERİ KALANINI yükler. -->

@core/CLAUDE.core.md

> Yukarıdaki import metodoloji çekirdeğini yükler (protokol, SORU 0, gate'ler). **Yasaklar
> yukarıda fiziksel damgalıdır — import'a bağlı değil** (junction kırılsa da anayasa yüklü;
> `check_kesin_yasaklar` guard'ı damganın kanonikle eşliğini zorlar).
> **Bu dosyada YALNIZ proje-özel bilgi durur.** Metodoloji buraya YAZILMAZ (SORU 0 → core).
> Not: Metodoloji dosyaları `core/` junction'ı altındadır; core dokümanlarındaki göreli
> yollar CORE köküne göredir. **Metodoloji araması DAİMA `path=core/` ile** (kök-Grep
> core'u görmez — D29).

## PROJE KİMLİĞİ

- **Profil:** `project.yaml` → `sap_profile: <ecc|s4_private|s4_public|btp_abap>` ·
  `release: "<REL>"` · `master_language: <ML>` · `source_root: <SOURCE_ROOT>`
- **SAP bağlantı:** `<PROJECT_ROOT>/.conn_adt` — Sistem: `<SYSTEM_ID>`, Client `<CLIENT>`,
  User: `<SAP_USER>`
- **Kaynak kod:** `<SOURCE_ROOT>/<MODULE>/<PKG>/` (L4 kuralları: her pakette `.rules.md`)

## PROJE-ÖZEL DOSYA İNDEKSİ

| Konu | Dosya |
|---|---|
| Paket listesi (auto-generated) | `governance/package-registry.md` |
| Proje ADR'leri (`<PROJE>-NNN` serisi) | `governance/decisions/` |
| Ertelenmiş iş tetikleri | `governance/deferred-triggers.md` |
| Proje-özel pattern/standart overlay | `playbook-local/` · `standards-local/` |
| Proje-özel validator'lar | `scripts/validators-local/` |

## PROJE-ÖZEL KURALLAR / AKTİF İŞ KÜLTÜRÜ

<!-- Proje-özel gate'ler, dondurulmuş-kök notları (frozen_readonly_paths), aktif sprint
     kültürü, müşteri-özel kısıtlar BURAYA. Örnek satırlar silinip doldurulur. -->
