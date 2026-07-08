# MAINTENANCE — Canlı-Çekirdek İşletimi

> DEV_CORE **tüm projelerin canlı metodolojisidir** (ADR 0020): buradaki her değişiklik
> junction'lı TÜM projelere anında yansır. Bu güç disiplinle dengelenir — bu doküman o
> disiplinin el kitabıdır.

## 1. Yazma disiplini — herkes PR + CI (bypass YOK)

- `main` korumalıdır: değişiklik = kısa branch → PR → **CI required-check yeşil** → merge
  (lider dahil; tek-kişi düzeninde `required_approving_review_count=0`, PR yine zorunlu).
- Trunk-based: `main` tek uzun-ömürlü branch; branch'ler aynı gün merge edilir.
- **Kim yazar:** davranış-yüzeyi (CLAUDE.core, hooks, guards, validators, MCP) = LİDER
  PR'ı. Alt-ajanlar core'a yazmaz (pre_tool_guard Ö5 yazım anında da tarar).
- Commit'ler `core.hooksPath=scripts/git-hooks` gate'inden geçer (`team_setup` kurar):
  genericize-leak + link-audit + applies_to şeması. CI aynı taramayı `--all` (tam-ağaç)
  koşar — hook atlanmış olsa bile merge edilemez.

## 2. Genericize-on-write (kimlik core'a GİREMEZ)

Proje/müşteri kimliği (sistem adı, kullanıcı, gerçek paket numaraları, eski-kök yolları)
core'a **commit'lenemez**. Placeholder'lar: `<SYSTEM_ID>`, `<SAP_USER>`, `<PROJECT_ROOT>`,
`ZSD<NNN>`. **İstisna:** `ZSD000`/`ZSD001` = çalışan-demo namespace (serbest);
`README.md`'de ilk-proje repo adı + tarihsel-yedek notu (gate allowlist'inde, gerekçeli).
Proje-özgü VERİ (sprint planı, legacy istisna listeleri, prefix'ler) core script'ine
değil **proje `project.yaml` / `governance/` dosyasına** gider (aşağıda katalog).

## 3. `applies_to` zorunluluğu (D21)

`standards/` + `playbook/` altındaki her `.md` frontmatter'da profil beyan eder:
`applies_to: [s4_private]` (enum: `profiles/*.yaml` adları + `all`). Typo = sessiz
profil-kaybı — gate şema doğrular. Yeni içerikte kanıtsız profil genişletme YAPMA
(yalnız doğrulandığın profili yaz).

## 3b. KESİN YASAKLAR fiziksel damgası (ADR 0021)

Yasaklar (ADR 0005: A/B/C/D + TAHMİN-YASAK) her projenin **kök `CLAUDE.md`'sine FİZİKSEL
damgalıdır** — `@import`'a/junction'a bağlı DEĞİL (junction kırılsa da anayasa yüklü).
- Tek kaynak: `claude/kesin-yasaklar.canonical.md`. Yeni proje: `init_project` damgalar.
- Kanonik değişirse (nadir): `python core/scripts/sync_yasaklar.py --root C:\IX` → tüm
  projeleri yeniden damgalar. `--check` ile önce sapanları gör.
- Damga elle düzenlenmez (marker'lar arası). Drift = `check_kesin_yasaklar` BLOCKER
  (run_all_validators + session_start + SAP-yazma öncesi pre_tool_guard).

## 4. `stable` tag + rollback

- `stable` = bilinen-iyi commit. Yalnız LİDER ilerletir (tag-ruleset korumalı):
  `git tag -f stable && git push -f origin stable` (GATE geçişlerinde).
- **Core kırıldıysa** (bir proje oturumu core hatasıyla bloke): `git -C C:\IX\DEV_CORE
  checkout stable` → tüm projeler anında bilinen-iyiye döner (session_start "detached@stable"
  durumunu SAKİN raporlar). Onarım sonrası dönüş: `git switch main`.
- Junction'a dokunulmaz — rollback tamamen git işlemidir.

## 5. Pull disiplini + drift

- Başka makine/PR'dan gelen core değişikliği makineye TEK yerden iner:
  `git -C C:\IX\DEV_CORE pull`. Projelerde pull YOKTUR (junction).
- `session_start` uyarıları: "core origin'in gerisinde" (saatte-1 throttle) ·
  junction kopuk (4'ü tek tek) · settings/shim template-drift (D7) ·
  behavior-manifest sapması (F2). Uyarı = önce core'u sağlıkla hizala, sonra işe devam.
- Manifest güncelleme (davranış-yüzeyi bilinçli değiştiğinde, PR içinde):
  `python scripts/behavior_manifest.py generate`.

## 6. project.yaml kataloğu (mekanizma core'da, DEĞER projede)

Okuma tek-noktası: `scripts/utils/project_config.py` (`cfg(key)`; env override:
`IX_<KEY_UPPER>`). Lite-parser: skaler + inline `[a, b]` + `- x` blok listeleri.

| Anahtar | Ne | Örnek |
|---|---|---|
| `source_root` | Kaynak-kod klasör adı (K12) | `SOURCE_CODES` |
| `repo_mode` | `full` / `local` / `none` (K13) | `full` |
| `sap_profile` | `ecc/s4_private/s4_public/btp_abap` | `s4_private` |
| `release` / `db` / `cleancore_policy` / `master_language` | Profil detayı | `"2025"` / — / `balanced` / `TR` |
| `frozen_readonly_paths` | Yazma-yasak kökler (freeze-guard R10; örn. dondurulmuş eski-dünya kökü) | `[C:/ESKI_KOK]` |
| `active_package` | Aktif paket (spec arama önceliği + hook mesajları) | `ZSD001_CLC` |
| `package_exceptions` | Paket-sınır istisnaları | `["ZSD001_CLC:^ZCL_..."]` |
| `sql_view_prefix` / `cds_view_name_prefix` | CDS namespace whitelist'i (B-5; eksikse populate NET hatayla durur) | `ZSD001_V_` / `zsd001_ddl_` |
| `cds_banned_literals` | Source-body yasak regex'leri (legacy ns) | `["\\bzsd_legacy_\\w+"]` |
| `cds_legacy_sqlview_exceptions` | Rename-imkansız eski sqlViewName'ler | `["ZSD001_DDL_X:ZSD01OLDSV"]` |
| `legacy_spec_roots` | Eski-sistem spec kökleri (td_spec_check fallback) | `[C:/.../LEGACY/MOD]` |
| `sprint_gates_file` | Sprint-gate tanım dosyası (varsayılan `governance/sprint-gates.json`; dosya yoksa gate SKIP) | — |
| `default_ui_root` | deploy_ui varsayılan UI kökü | `SOURCE_CODES/SD/ZSD001_CLC/ui` |
| `doctor_probe_object` | sap_doctor canlı-okuma probu | `ZSD001_I_ORDER` |
| `kd_docs_dir` / `kd_help_dir` | KD/PDF üretim yolları | — |
| `mail_attachments` | send_mail ekleri | — |

Dosya-tabanlı olanlar: `.claude/watchdog_probes` ("path|desen" satırları — agent_watchdog),
`governance/sprint-gates.json` (sprint tanımları).

## 7. Yeni içerik nereye? (SORU 0 kısa aynası)

Projeye-özel değer/istisna → **proje** (`project.yaml`, `*-local/`, `.rules.md`).
Tüm projelere genellenebilir yöntem/ders → **core** (PR ile; genericize + `applies_to`).
Emin değilsen: önce proje-tarafına yaz, genellenince core'a PR'la terfi ettir.

## 8. Kurulum onarımı

`python scripts/team_setup.py` idempotenttir (eksik olanı tamamlar) ·
`--repair-junctions` kopuk junction onarır · `python scripts/ix_doctor.py` 7-katman
sağlık taraması *(Faz-F'de eklenir)* · Doğrulama komutu:
`python scripts/validators/run_all_validators.py` (CORE modunda scope=project SKIP'ler).
